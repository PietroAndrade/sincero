"""
Generate the code of the API's `.proto` files, for both sides:

    python tools/gen_proto.py                     # rewrite app/gen/ and ../frontend/src/gen/ (`make proto`)
    python tools/gen_proto.py --check             # exit 1 with a diff if either is stale (`make proto-check`)
    python tools/gen_proto.py --only python       # one side

    python       app/gen/                 protoc-gen-py (messages, protobuf-py runtime) and
                                          protoc-gen-connectrpc (the `Simulations` service: server
                                          Protocol, ASGI/WSGI apps, clients; connectrpc runtime)
    typescript   ../frontend/src/gen/     protoc-gen-es (messages and the service descriptor)

The files are every `proto/sincero/*.proto` plus the vendored `proto/google/rpc/error_details.proto`
(the `ErrorInfo` / `BadRequest` error details). protoc is grpcio-tools' (as for `gen_dto.py`);
`buf/validate/validate.proto` resolves offline from `proto/buf_validate.binpb` and is not
generated: both sides import it from their protovalidate package (`map_imports`).

The Python plugins are looked up next to the running interpreter (`requirements-dev.txt`), the
TypeScript one in `../frontend/node_modules` (`npm ci` in ../frontend; `make proto` does it).
The output directories are wiped and rewritten: never edit them by hand.
`tests/test_gen_proto.py` fails while they and the `.proto` files disagree.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.resources
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

BACKEND = Path(__file__).resolve().parent.parent
PROTO_DIR = BACKEND / "proto"
BUF_VALIDATE = PROTO_DIR / "buf_validate.binpb"
FRONTEND = BACKEND.parent / "frontend"
VENDORED = ("google/rpc/error_details.proto",)
SKIP = {"__pycache__"}


class GeneratorError(RuntimeError):
    """A plugin is missing or protoc failed."""


@dataclass(frozen=True)
class Plugin:
    name: str            # protoc-gen-<name>, --<name>_out
    path: Path
    options: str = ""


@dataclass(frozen=True)
class Target:
    name: str
    out: Path
    plugins: tuple[Plugin, ...]
    install_hint: str

    def missing(self) -> list[Path]:
        return [p.path for p in self.plugins if not p.path.exists()]


_PY_BIN = Path(sys.executable).parent
TARGETS: dict[str, Target] = {
    "python": Target("python", BACKEND / "app" / "gen", (
        Plugin("py", _PY_BIN / "protoc-gen-py", "map_imports=buf/validate/:protovalidate._gen"),
        Plugin("connectrpc", _PY_BIN / "protoc-gen-connectrpc"),
    ), "pip install -r requirements-dev.txt"),
    "typescript": Target("typescript", FRONTEND / "src" / "gen", (
        Plugin("es", FRONTEND / "node_modules" / ".bin" / "protoc-gen-es",
               "target=ts,import_extension=js,map_imports=buf/validate/:@bufbuild/protovalidate/gen"),
    ), "npm ci --prefix ../frontend"),
}


def protos() -> list[str]:
    """The files to generate, relative to proto/, in a stable order."""
    return sorted(p.relative_to(PROTO_DIR).as_posix() for p in (PROTO_DIR / "sincero").glob("*.proto")) + list(VENDORED)


# ----- protoc ------------------------------------------------------------------------------------
def generate(target: Target, out: Path) -> None:
    """Run protoc with the target's plugins into `out` (which must exist)."""
    missing = target.missing()
    if missing:
        raise GeneratorError(f"{target.name}: plugin not found: {', '.join(map(str, missing))} ({target.install_hint})")
    from grpc_tools import protoc

    args = ["protoc", f"-I{PROTO_DIR}", f"-I{importlib.resources.files('grpc_tools') / '_proto'}",
            f"--descriptor_set_in={BUF_VALIDATE}"]
    for p in target.plugins:
        args += [f"--plugin=protoc-gen-{p.name}={p.path}", f"--{p.name}_out={out}"]
        if p.options:
            args.append(f"--{p.name}_opt={p.options}")
    if protoc.main([*args, *protos()]) != 0:
        raise GeneratorError(f"{target.name}: protoc failed")


def read_tree(root: Path) -> dict[str, str]:
    """Every file under `root` by relative path, skipping caches."""
    if not root.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_file() and not SKIP & set(p.relative_to(root).parts)}


def render(target: Target) -> dict[str, str]:
    """What the target's directory must contain, freshly generated."""
    with tempfile.TemporaryDirectory() as tmp:
        generate(target, Path(tmp))
        return read_tree(Path(tmp))


def stale(target: Target) -> list[str]:
    """A unified diff, committed -> fresh; empty when the committed code is up to date."""
    current, fresh = read_tree(target.out), render(target)
    label = target.out.relative_to(BACKEND.parent).as_posix()
    lines: list[str] = []
    for path in sorted(current.keys() | fresh.keys()):
        old, new = current.get(path, ""), fresh.get(path, "")
        if old != new:
            lines += difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                          f"{label}/{path}" if path in current else "/dev/null",
                                          f"generated/{path}" if path in fresh else "/dev/null")
    return lines


def write(target: Target) -> None:
    shutil.rmtree(target.out, ignore_errors=True)
    target.out.mkdir(parents=True)
    generate(target, target.out)


# ----- command line ------------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="generate app/gen/ and ../frontend/src/gen/ from proto/")
    ap.add_argument("--check", action="store_true", help="exit 1 (with a diff) if the generated code is stale")
    ap.add_argument("--only", choices=sorted(TARGETS), help="one side only")
    args = ap.parse_args(argv)
    targets = [TARGETS[args.only]] if args.only else list(TARGETS.values())

    status = 0
    for target in targets:
        where = target.out.relative_to(BACKEND.parent)
        try:
            if args.check:
                diff = stale(target)
                if diff:
                    sys.stdout.writelines(diff)
                    print(f"{where}/ is stale: run `make proto`", file=sys.stderr)
                    status = 1
                else:
                    print(f"{where}/ is up to date")
            else:
                write(target)
                print(f"generated {where}/")
        except GeneratorError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    return status


if __name__ == "__main__":
    sys.exit(main())
