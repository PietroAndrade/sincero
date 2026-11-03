"""
Generate the input schemas of `openapi.yaml` from `proto/sincero/simulation_input.proto`.

    python ../docs/experiments/openapi/gen_openapi.py             # rewrite the generated block of openapi.yaml in place
    python ../docs/experiments/openapi/gen_openapi.py --check     # exit 1 (with a diff) if the block is stale
    python ../docs/experiments/openapi/gen_openapi.py --stdout    # print the block

Run from `backend/` with the project's virtualenv (see README.md in this directory). An experiment:
nothing in the application or its `make` targets uses it.

`openapi.yaml` is hand-written — routes, responses, error codes and examples are design, and
no protoc plugin can derive them from a `.proto` that declares no service. What the `.proto`
*does* state is generated, between two marker comments under `components.schemas`:

    InputFields        every input field: name, order, type, nullability, default, description,
                       owning group (`x-group`) — from the .proto;
                       the API ceiling (`maximum` / `maxItems`) and unit (`x-unit`) — from the
                       controller, which owns them (app/controllers/api_requests.py)
    SimulationInput    InputFields with the required fields required

Everything else in the file refers to these two by `$ref`. Needs `grpcio-tools`
(requirements-dev.txt).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))   # `app` and `tools` as packages, when run as a script

from app.controllers.api_requests import DEFAULT_NAME, GROUP_NAMES, MAX_BALLOONS, UNITS, UPPER_BOUNDS   # noqa: E402
from app.models.input_dto import INPUT_GROUPS                                                         # noqa: E402
from tools.gen_dto import PROTO, PROTO_DIR, Group, compile_proto, read_groups               # noqa: E402

TARGET = HERE / "openapi.yaml"
BEGIN = "    # >>> generated from proto/sincero/simulation_input.proto by gen_openapi.py — do not edit this block"
END = "    # <<< end of the generated block"
INDENT = 4            # the block sits under `components: / schemas:`

PY_TO_JSON = {"str": "string", "float": "number", "int": "integer"}
GROUP_NAME = {dto.__base__.__name__: name for dto, name in GROUP_NAMES.items()}   # ContractFields -> contract


# ----- the schemas, as plain dicts ----------------------------------------------------------
def _property(field, group: Group) -> dict[str, Any]:
    """The JSON Schema of one input field."""
    schema: dict[str, Any] = {}
    match = re.fullmatch(r"(?:Optional\[(\w+)\]|tuple\[(\w+), \.\.\.\]|(\w+))", field.annotation)
    nullable, item, plain = match.groups()
    if field.repeated:
        schema["type"] = "array"
        schema["items"] = {"type": PY_TO_JSON[item]}
        schema["maxItems"] = MAX_BALLOONS
    elif nullable:
        schema["type"] = [PY_TO_JSON[nullable], "null"]
    else:
        schema["type"] = PY_TO_JSON[plain]
    if field.comment:
        schema["description"] = " ".join(field.comment)
    if field.default is not None:
        schema["default"] = [] if field.repeated else eval(field.default)          # the generated python literal
    elif field.name == "name":
        schema["default"] = DEFAULT_NAME                                        # the controllers' label for an unnamed input
    if field.name in UPPER_BOUNDS:
        schema["maximum"] = UPPER_BOUNDS[field.name]
    schema["x-group"] = GROUP_NAME[group.class_name]
    if UNITS.get(field.name):
        schema["x-unit"] = UNITS[field.name]
    return schema


def schemas(groups: tuple[Group, ...]) -> dict[str, Any]:
    """`InputFields` and `SimulationInput`, in the order they appear in the block."""
    properties = {f.name: _property(f, g) for g in groups for f in g.fields}
    required = [f.name for g in groups for f in g.fields if f.default is None and f.name != "name"]
    return {
        "InputFields": {
            "type": "object",
            "description": "Any subset of the input fields of a simulation — a `base`, a candidate, a variation, "
                           "the `overrides` of a what-if row. Field names are the model's; the grouping into "
                           "`contract` / `market` / `bank_credit` (`x-group`) is not visible on the wire. "
                           "Types are strict JSON types: a number field takes only a JSON number, an integer "
                           "field a JSON number without fractional part (`19.0` is fine, `19.5` is not). "
                           "`null` is accepted only where the type says so and means \"absent\". "
                           "Generated from `proto/sincero/simulation_input.proto`.",
            "additionalProperties": False,
            "properties": properties,
        },
        "SimulationInput": {
            "description": "The body of `POST /api/simulations`: the input fields with the required ones present. "
                           "Omitted fields take their `default`.",
            "allOf": [{"$ref": "#/components/schemas/InputFields"}],
            "required": required,
        },
    }


# ----- a small YAML emitter (block style, deterministic, no dependency) ----------------------------
_PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]*")
_RESERVED = {"true", "false", "null", "yes", "no", "on", "off", "y", "n", "~"}


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        if _PLAIN.fullmatch(value) and value.lower() not in _RESERVED:
            return value
        return json.dumps(value, ensure_ascii=False)           # a JSON string is a valid YAML double-quoted scalar
    raise TypeError(f"cannot emit {value!r}")


def emit(value: Any, indent: int) -> list[str]:
    pad = " " * indent
    lines: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, dict) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(emit(item, indent + 2))
            elif isinstance(item, list) and item and any(isinstance(x, (dict, list)) for x in item):
                lines.append(f"{pad}{key}:")
                for x in item:
                    sub = emit(x, indent + 4)
                    lines.append(f"{pad}  - {sub[0].lstrip()}")
                    lines.extend(sub[1:])
            elif isinstance(item, list):
                lines.append(f"{pad}{key}: [{', '.join(_scalar(x) for x in item)}]")
            elif isinstance(item, dict):
                lines.append(f"{pad}{key}: {{}}")
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
        return lines
    raise TypeError(f"cannot emit {value!r} at top level")


def render_block(groups: Optional[tuple[Group, ...]] = None) -> str:
    """The generated block, markers included, indented for `components.schemas`."""
    if groups is None:
        groups = read_groups(compile_proto(PROTO, [PROTO_DIR]), PROTO)
    body = emit(schemas(groups), INDENT)
    return "\n".join([BEGIN, *body, END]) + "\n"


# ----- splicing into openapi.yaml ------------------------------------------------------------------
def split(text: str) -> tuple[str, str, str]:
    """(before, block, after) of the file's generated block; raises if the markers are missing."""
    start, end = text.find(BEGIN), text.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{TARGET.name}: the generated block's markers are missing or out of order")
    end += len(END) + 1
    return text[:start], text[start:end], text[end:]


def spliced(text: str, block: str) -> str:
    before, _, after = split(text)
    return before + block + after


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=f"generate the input schemas of {TARGET.name} from proto/{PROTO}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 if the generated block is stale")
    mode.add_argument("--stdout", action="store_true", help="print the block instead of writing")
    args = ap.parse_args(argv)

    block = render_block()
    if args.stdout:
        sys.stdout.write(block)
        return 0
    current = TARGET.read_text(encoding="utf-8")
    updated = spliced(current, block)
    if args.check:
        if current == updated:
            return 0
        sys.stdout.writelines(difflib.unified_diff(current.splitlines(True), updated.splitlines(True),
                                                   TARGET.name, "generated"))
        print(f"{TARGET.name}: the generated block is stale: run gen_openapi.py", file=sys.stderr)
        return 1
    TARGET.write_text(updated, encoding="utf-8")
    print(f"{'updated' if current != updated else 'unchanged'} {TARGET.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
