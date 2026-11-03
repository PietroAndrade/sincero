"""
Generate `app/models/input_fields.py` — the fields of the input DTOs — from
`proto/sincero/simulation_input.proto`.

    python tools/gen_dto.py             # rewrite app/models/input_fields.py
    python tools/gen_dto.py --check     # exit 1 (with a diff) if the file is stale; what `make test` does
    python tools/gen_dto.py --stdout    # print the generated module

The .proto declares the `SimulationInput` message: one flat list of fields, each tagged with
the `(sincero.field)` option (owning `Group`, default, nullable). This script turns every
group into a frozen dataclass named `<Group>Fields`, fields in .proto order, with:

    plain scalar                      ->  `name: type`                       (required)
    optional scalar + default_*       ->  `name: type = default`
    optional scalar + nullable        ->  `name: Optional[type] = None`
    repeated scalar                   ->  `name: tuple[type, ...] = field(default_factory=tuple)`,
                                          normalised to a tuple in `__post_init__`

and refuses anything else (an `optional` without a meaning, a default of the wrong type, a
required field after an optional one, a field without a group, a type it does not map).
The leading comment of a field becomes a comment above it; the comment of a `Group` value
becomes the docstring of its dataclass.

Needs `grpcio-tools` (requirements-dev.txt); the generated module needs nothing.
"""
from __future__ import annotations

import argparse
import difflib
import importlib
import importlib.resources
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from google.protobuf import descriptor_pb2, descriptor_pool

BACKEND = Path(__file__).resolve().parent.parent
PROTO_DIR = BACKEND / "proto"
PROTO = "sincero/simulation_input.proto"
MESSAGE = "SimulationInput"
TARGET = BACKEND / "app" / "models" / "input_fields.py"

_FD = descriptor_pb2.FieldDescriptorProto

# proto scalar type -> (python type, the `default` member of FieldMeta it must use)
SCALARS: dict[int, tuple[str, str]] = {
    _FD.TYPE_DOUBLE: ("float", "default_number"),
    _FD.TYPE_FLOAT: ("float", "default_number"),
    _FD.TYPE_INT32: ("int", "default_integer"),
    _FD.TYPE_INT64: ("int", "default_integer"),
    _FD.TYPE_SINT32: ("int", "default_integer"),
    _FD.TYPE_SINT64: ("int", "default_integer"),
    _FD.TYPE_STRING: ("str", "default_string"),
}


class GeneratorError(ValueError):
    """The .proto breaks one of the conventions stated in its header."""


# ----- what the generator reads from the .proto ---------------------------------------------
@dataclass(frozen=True)
class Field:
    name: str
    annotation: str            # `float`, `Optional[float]`, `tuple[int, ...]`
    default: Optional[str]     # python source of the default; None = required
    repeated: bool
    comment: tuple[str, ...]   # the leading comment, line by line


@dataclass(frozen=True)
class Group:
    name: str                  # the enum value: CONTRACT
    class_name: str            # ContractFields
    doc: str
    fields: tuple[Field, ...]


# ----- protoc ---------------------------------------------------------------------------------
def _google_include() -> str:
    """Where grpcio-tools keeps google/protobuf/descriptor.proto."""
    return str(importlib.resources.files("grpc_tools") / "_proto")


def compile_proto(proto: str, include: Sequence[Path]) -> descriptor_pb2.FileDescriptorSet:
    """
    Run protoc on `proto` (a path relative to one of `include`). Returns the descriptors of
    the file and its imports, with source info (comments). The generated `_pb2` module is
    imported for its side effect: it registers the `(sincero.field)` extension in the default
    descriptor pool, which is what lets the options be read as `FieldMeta` messages.
    """
    try:
        from grpc_tools import protoc
    except ImportError as exc:                           # pragma: no cover
        raise GeneratorError("grpcio-tools is not installed: pip install -r requirements-dev.txt") from exc

    module_name = proto[: -len(".proto")].replace("/", ".") + "_pb2"
    with tempfile.TemporaryDirectory() as tmp:
        args = ["protoc", *[f"-I{p}" for p in include], f"-I{_google_include()}", f"--python_out={tmp}",
                f"--descriptor_set_out={tmp}/set.pb", "--include_source_info", "--include_imports", proto]
        if protoc.main(args) != 0:
            raise GeneratorError(f"protoc failed on {proto}")
        sys.path.insert(0, tmp)
        try:
            importlib.import_module(module_name)
        finally:
            sys.path.remove(tmp)
        return descriptor_pb2.FileDescriptorSet.FromString(Path(tmp, "set.pb").read_bytes())


# ----- from descriptors to groups ----------------------------------------------------------------
def _comments(file: descriptor_pb2.FileDescriptorProto) -> dict[tuple[int, ...], tuple[str, ...]]:
    """Leading comment of every element, keyed by its path in the descriptor, as clean lines."""
    out = {}
    for loc in file.source_code_info.location:
        if loc.leading_comments:
            out[tuple(loc.path)] = tuple(line.strip() for line in loc.leading_comments.strip("\n").splitlines())
    return out


def _python_default(meta, kind: str, field_name: str, expected: str) -> str:
    value = getattr(meta, kind)
    if kind != expected:
        raise GeneratorError(f"{field_name}: {kind} does not match the field's type (expected {expected})")
    return repr(float(value)) if kind == "default_number" else repr(value)


def read_groups(fds: descriptor_pb2.FileDescriptorSet, proto: str, message: str = MESSAGE) -> tuple[Group, ...]:
    """The groups of `message` in `proto`, each with its fields in .proto order; raises `GeneratorError`."""
    pool = descriptor_pool.Default()
    ext = pool.FindExtensionByName("sincero.field")
    group_enum = pool.FindEnumTypeByName("sincero.Group")
    files = {f.name: f for f in fds.file}
    file = files[proto]
    comments = _comments(file)

    msg_index, msg = next((i, m) for i, m in enumerate(file.message_type) if m.name == message)
    by_group: dict[str, list[Field]] = {v.name: [] for v in group_enum.values if v.number != 0}

    for field_index, f in enumerate(msg.field):
        if not f.options.HasExtension(ext):
            raise GeneratorError(f"{f.name}: missing the (sincero.field) option")
        meta = f.options.Extensions[ext]
        if meta.group == 0:
            raise GeneratorError(f"{f.name}: group is unspecified")
        group = group_enum.values_by_number[meta.group].name
        if f.type not in SCALARS:
            raise GeneratorError(f"{f.name}: unsupported type {_FD.Type.Name(f.type)}")
        py_type, default_kind = SCALARS[f.type]
        default_set = meta.WhichOneof("default")
        repeated = f.label == _FD.LABEL_REPEATED

        if repeated:
            if default_set or meta.nullable:
                raise GeneratorError(f"{f.name}: a repeated field is always a tuple, empty by default")
            annotation, default = f"tuple[{py_type}, ...]", "field(default_factory=tuple)"
        elif f.proto3_optional:
            if default_set and meta.nullable:
                raise GeneratorError(f"{f.name}: either a default or nullable, not both")
            if meta.nullable:
                annotation, default = f"Optional[{py_type}]", "None"
            elif default_set:
                annotation, default = py_type, _python_default(meta, default_set, f.name, default_kind)
            else:
                raise GeneratorError(f"{f.name}: optional, but neither a default nor nullable — what does omitting it mean?")
        else:
            if default_set or meta.nullable:
                raise GeneratorError(f"{f.name}: a required field cannot have a default or be nullable; mark it optional")
            annotation, default = py_type, None

        fields = by_group[group]
        if default is None and fields and fields[-1].default is not None:
            raise GeneratorError(f"{f.name}: required field after an optional one in group {group}")
        fields.append(Field(f.name, annotation, default, repeated, comments.get((4, msg_index, 2, field_index), ())))

    enum_file = files[group_enum.file.name]              # where `Group` is declared: its comments are the docstrings
    enum_index = next(i for i, e in enumerate(enum_file.enum_type) if e.name == group_enum.name)
    enum_comments = _comments(enum_file)
    groups = []
    for value_index, value in enumerate(group_enum.values):
        if value.number == 0:
            continue
        doc = " ".join(enum_comments.get((5, enum_index, 2, value_index), ()))
        if not doc:
            raise GeneratorError(f"Group.{value.name}: needs a comment — it is the dataclass docstring")
        if not by_group[value.name]:
            raise GeneratorError(f"Group.{value.name}: no field belongs to it")
        class_name = "".join(part.capitalize() for part in value.name.split("_")) + "Fields"
        groups.append(Group(value.name, class_name, doc, tuple(by_group[value.name])))
    return tuple(groups)


# ----- rendering ----------------------------------------------------------------------------------
HEADER = '''"""
The fields of a simulation input, one frozen dataclass per group.

GENERATED by tools/gen_dto.py from proto/{proto} — DO NOT EDIT.
Regenerate with `make dto`; `make test` fails while this file and the .proto disagree.

The DTOs the application uses are in `input_dto.py`: they subclass these classes and add
only derived amounts. Field names, types, defaults, nullability and grouping are decided
in the .proto.
"""
from __future__ import annotations

'''


def render_groups(groups: Sequence[Group], proto: str = PROTO) -> str:
    any_repeated = any(f.repeated for g in groups for f in g.fields)
    any_optional = any(f.annotation.startswith("Optional[") for g in groups for f in g.fields)
    out = [HEADER.format(proto=proto)]
    out.append(f"from dataclasses import dataclass{', field' if any_repeated else ''}\n")
    if any_optional:
        out.append("from typing import Optional\n")
    for group in groups:
        out.append("\n\n@dataclass(frozen=True)\n")
        out.append(f"class {group.class_name}:\n")
        out.append(f'    """{group.doc}"""\n\n')
        for f in group.fields:
            for line in f.comment:
                out.append(f"    # {line}\n")
            out.append(f"    {f.name}: {f.annotation}" + (f" = {f.default}\n" if f.default is not None else "\n"))
        repeated = [f for f in group.fields if f.repeated]
        if repeated:
            out.append("\n    def __post_init__(self):\n")
            for f in repeated:
                out.append(f'        object.__setattr__(self, "{f.name}", tuple(self.{f.name}))\n')
    return "".join(out)


def render(proto: str = PROTO, include: Sequence[Path] = (PROTO_DIR,), message: str = MESSAGE) -> str:
    """The generated module for `proto`, as text."""
    return render_groups(read_groups(compile_proto(proto, include), proto, message), proto)


# ----- command line ----------------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=f"generate {TARGET.relative_to(BACKEND)} from proto/{PROTO}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 if the generated file is stale")
    mode.add_argument("--stdout", action="store_true", help="print instead of writing")
    args = ap.parse_args(argv)

    try:
        source = render()
    except GeneratorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.stdout:
        sys.stdout.write(source)
        return 0
    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if args.check:
        if current == source:
            return 0
        sys.stdout.writelines(difflib.unified_diff(current.splitlines(True), source.splitlines(True),
                                                   str(TARGET.relative_to(BACKEND)), "generated"))
        print(f"{TARGET.relative_to(BACKEND)} is stale: run `make dto`", file=sys.stderr)
        return 1
    TARGET.write_text(source, encoding="utf-8")
    print(f"{'updated' if current != source else 'unchanged'} {TARGET.relative_to(BACKEND)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
