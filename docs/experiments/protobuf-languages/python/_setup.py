"""
Shared by the Python experiment: compile the protos into a temporary directory and import them.

    backend/proto/sincero/simulation_input.proto   -> sincero.simulation_input_pb2   (grpcio-tools' protoc)
    ../proto/sincero_rules.proto                   -> sincero_rules_pb2               (+ buf/validate/validate_pb2,
                                                      from the descriptor set ../proto/buf_validate.binpb)

Run from anywhere with the backend's virtualenv: it needs `grpcio-tools`, `protobuf` and
`protovalidate` (`pip install protovalidate`).
"""
from __future__ import annotations

import importlib
import importlib.resources
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                      # the repository
BACKEND = ROOT / "backend"
PROTO = HERE.parent / "proto"
sys.path.insert(0, str(BACKEND))

from grpc_tools import protoc  # noqa: E402


def compile_all():
    out = tempfile.mkdtemp(prefix="sincero-proto-")
    include = str(importlib.resources.files("grpc_tools") / "_proto")
    common = ["protoc", f"-I{BACKEND / 'proto'}", f"-I{PROTO}", f"-I{include}", f"--python_out={out}"]
    assert protoc.main([*common, "sincero/simulation_input.proto"]) == 0
    assert protoc.main([*common, f"--descriptor_set_in={PROTO / 'buf_validate.binpb'}",
                        "buf/validate/validate.proto", "sincero_rules.proto"]) == 0
    sys.path.insert(0, out)
    return importlib.import_module("sincero.simulation_input_pb2"), importlib.import_module("sincero_rules_pb2")


pb, rules_pb = compile_all()
