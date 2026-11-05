"""
The ways a required field can be protected against being absent, enforced by `protovalidate`
(../proto/presence_variants.proto) — the evidence for
docs/decisions/required-fields-explicit-presence.md.

    cd backend && .venv/bin/python ../docs/experiments/protobuf-languages/python/presence.py

Each body goes through the proto3 JSON mapping (`json_format.ParseDict`, as a Connect server
parses it) and then `protovalidate`. `present` is `HasField` (n/a without explicit presence);
`wire` is the size of the binary encoding — 0 bytes means the value does not reach the other side.
"""
from __future__ import annotations

import protovalidate
from google.protobuf import json_format

from _setup import presence_pb


def outcome(message_type, body: dict) -> str:
    """`accepted`, or the violations, for one JSON body."""
    msg = json_format.ParseDict(body, message_type())
    try:
        protovalidate.validate(msg)
        return "accepted"
    except protovalidate.ValidationError as exc:
        return "refused: " + "; ".join(v.proto.message for v in exc.violations)


def present(message_type, body: dict) -> str:
    field = message_type.DESCRIPTOR.fields[0]
    return str(json_format.ParseDict(body, message_type()).HasField(field.name)) if field.has_presence else "n/a"


def wire(message_type, body: dict) -> int:
    return len(json_format.ParseDict(body, message_type()).SerializeToString())


def bodies(message_type) -> list[dict]:
    name = message_type.DESCRIPTOR.fields[0].name
    valid = 5 if name == "amount" else 19
    return [{}, {name: None}, {name: 0}, {name: valid}]


VARIANTS = [presence_pb.A_PlainRejectZero, presence_pb.B_PlainRequired, presence_pb.C_OptionalOnly,
            presence_pb.D_OptionalRequired, presence_pb.E_PlainCelHas, presence_pb.F_PlainZeroIsValid,
            presence_pb.G_OptionalRequiredZeroIsValid]

if __name__ == "__main__":
    for variant in VARIANTS:
        print(f"# {variant.DESCRIPTOR.name}")
        for body in bodies(variant):
            print(f"  {str(body):28} {outcome(variant, body):88} present={present(variant, body):5} wire={wire(variant, body)}")
