"""
The model's validation rules declared in the .proto (../proto/sincero_rules.proto,
`buf.validate` constraints + one CEL expression) and enforced by `protovalidate` — the same
file the TypeScript experiment enforces with `@bufbuild/protovalidate`.

    cd backend && .venv/bin/python ../docs/experiments/protobuf-languages/python/rules.py
"""
from __future__ import annotations

import protovalidate
from google.protobuf import json_format

from _setup import rules_pb


def violations(**fields) -> list[str]:
    return _violations(rules_pb.ValidatedInput(**fields))


def violations_of_body(body: dict) -> list[str]:
    """
    The same rules on a JSON body, parsed as a Connect server parses it (the proto3 JSON mapping).
    `ValidatedInput` copies six of the sixteen input fields, so the other keys are ignored here.
    """
    return _violations(json_format.ParseDict(body, rules_pb.ValidatedInput(), ignore_unknown_fields=True))


def simulate_if_valid(body: dict):
    """
    The order a server keeps: the rules of the .proto first, the model only for a body they accept.
    Returns the violations (the model never ran) or the model's `SimulationResult`.
    """
    refused = violations_of_body(body)
    if refused:
        return refused
    from app.models import field_defaults, simulate           # the backend's model, unchanged
    from app.views import input_from_dict
    return simulate(input_from_dict({**field_defaults(), "name": "CUSTOM", **body}))


def _violations(msg) -> list[str]:
    try:
        protovalidate.validate(msg)
        return []
    except protovalidate.ValidationError as exc:
        return [f"{_path(v.proto) or '(message)'}: {v.proto.message}" for v in exc.violations]


def _path(violation) -> str:
    """`balloon_months.[2]` — the field path of a violation, as the TypeScript experiment prints it."""
    parts = []
    for e in violation.field.elements if violation.has_field("field") else ():
        parts.append(e.field_name)
        if e.subscript is not None and e.subscript.field == "index":
            parts.append(f"[{e.subscript.value}]")
    return ".".join(parts)


CASES = [
    ("RA", dict(list_price=440000, months_remaining=19, fgts_upfront=13000, balloon_months=[6, 12])),
    ("list price 0, months 0", dict(list_price=0, months_remaining=0)),
    ("list price and months absent", dict()),
    ("months absent", dict(list_price=440000)),
    ("list price absent, FGTS set (the CEL rule stays quiet)", dict(months_remaining=19, fgts_upfront=13000)),
    ("months 5000", dict(list_price=440000, months_remaining=5000)),
    ("down payment 150 %", dict(list_price=440000, months_remaining=19, down_payment_pct=150)),
    ("repeated balloon, balloon 0", dict(list_price=440000, months_remaining=19, balloon_months=[6, 6, 0])),
    ("upfront above the price (CEL)", dict(list_price=440000, months_remaining=19, fgts_upfront=300000, cash_upfront=140001)),
]

if __name__ == "__main__":
    for label, fields in CASES:
        v = violations(**fields)
        print(f"# {label}\n  " + ("\n  ".join(v) if v else "valid"))
