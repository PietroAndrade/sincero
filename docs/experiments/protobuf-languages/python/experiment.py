"""
Python × protobuf — the same experiment as ../typescript and ../csharp, for the comparison.

    cd backend && .venv/bin/python ../docs/experiments/protobuf-languages/python/experiment.py

The `(sincero.field)` option through the descriptor, a `resolve()` applying the defaults, the
three DTOs as a split by group, the contract's JSON bodies through `json_format.ParseDict`
— and the application's hand-written shape layer (`app/controllers/api_requests.py`) on the
same bodies, for reference.
"""
from __future__ import annotations

import json
import math
import timeit

from _setup import pb                                           # compiles and imports the .proto
from google.protobuf import json_format

from app.controllers.api_requests import ApiError, simulation_input   # the shape layer, for reference

# ----- 1. the DTO: the generated message is NOT the domain's DTO in Python -------------------------
# `pb.SimulationInput` is mutable, unhashable and zero-valued; the application generates frozen
# dataclasses from the same .proto instead (backend/tools/gen_dto.py). Here the message is used
# directly, as TypeScript and C# do, to compare the glue needed.
def required_down_payment(c) -> float:
    return c.list_price * (c.down_payment_pct if c.HasField("down_payment_pct") else 20.0) / 100.0


def upfront(c) -> float:
    return (c.fgts_upfront if c.HasField("fgts_upfront") else 0.0) + (c.cash_upfront if c.HasField("cash_upfront") else 0.0)


def remaining_down_payment(c) -> float:
    return max(0.0, required_down_payment(c) - upfront(c))


# ----- 2. what the .proto says about each field, read from the custom option ---------------------------
DEFAULT_NAME = "CUSTOM"   # the controllers' label for an unnamed input (api-contract, open question)
FIELDS = []
for f in pb.SimulationInput.DESCRIPTOR.fields:
    meta = f.GetOptions().Extensions[pb.field]                 # (sincero.field) — a typed FieldMeta
    kind = meta.WhichOneof("default")
    FIELDS.append(dict(name=f.name, field=f, group=pb.Group.Name(meta.group).lower(), nullable=meta.nullable,
                       required=not f.is_repeated and (not f.has_presence or not (kind or meta.nullable)),   # a plain scalar, or `optional` with no meaning for omission
                       default=[] if f.is_repeated else (getattr(meta, kind) if kind else None)))


# ----- 3. resolve: defaults applied, required fields checked --------------------------------------------
def resolve(msg):
    out = pb.SimulationInput()
    out.CopyFrom(msg)
    for info in FIELDS:
        f = info["field"]
        is_set = out.HasField(f.name) if f.has_presence else bool(getattr(out, f.name))   # implicit presence: 0 reads as unset
        if info["name"] == "name" and not is_set:
            out.name = DEFAULT_NAME
            continue
        if info["required"] and not is_set:
            raise ValueError(f"{info['name']} is required")
        if not is_set and info["default"] not in (None, []) and not info["nullable"]:
            setattr(out, f.name, info["default"])
    return out


# ----- 4. the three DTOs, as a split by group ------------------------------------------------------------
def split(msg):
    groups = {"contract": {}, "market": {}, "bank_credit": {}}
    for info in FIELDS:
        f = info["field"]
        value = getattr(msg, f.name)
        groups[info["group"]][f.name] = (None if f.has_presence and not msg.HasField(f.name)
                                         else list(value) if f.is_repeated else value)
    return groups


# ----- 5. the contract's bodies ------------------------------------------------------------------------------
MINIMAL = {"list_price": 440000, "months_remaining": 19}
RA = {"name": "RA", "list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000,
      "developer_installment": 2500, "balloon_months": [6, 12]}
CASES = [
    ("body is an array", [1, 2], "400 wrong_type body"),
    ("string for a number", {"list_price": "440000", "months_remaining": 19}, "400 wrong_type list_price"),
    ("boolean for a number", {"list_price": True, "months_remaining": 19}, "400 wrong_type list_price"),
    ("19.0 for an integer", {"list_price": 440000, "months_remaining": 19.0}, "accepted (19)"),
    ("19.5 for an integer", {"list_price": 440000, "months_remaining": 19.5}, "400 wrong_type months_remaining"),
    ('"19" for an integer', {"list_price": 440000, "months_remaining": "19"}, "400 wrong_type months_remaining"),
    ("true for an integer", {"list_price": 440000, "months_remaining": True}, "400 wrong_type months_remaining"),
    ("two unknown fields", {**MINIMAL, "fgts_upfrnt": 13000, "foo": 1}, "400 unknown_field fgts_upfrnt"),
    ("camelCase alias", {"listPrice": 440000, "monthsRemaining": 19}, "400 unknown_field listPrice"),
    ("missing months_remaining", {"list_price": 440000}, "400 missing_field months_remaining"),
    ("null on itbi_pct", {**MINIMAL, "itbi_pct": None}, "400 null_not_allowed itbi_pct"),
    ("null on developer_installment", {**MINIMAL, "developer_installment": None}, "accepted (absent)"),
    ("NaN (parsed float)", {"list_price": math.nan, "months_remaining": 19}, "400 not_finite list_price"),
    ('"NaN" (string)', {"list_price": "NaN", "months_remaining": 19}, "400 wrong_type list_price"),
    ("list_price 10**400", {"list_price": 10 ** 400, "months_remaining": 19}, "400 not_finite list_price"),
    ("months_remaining 5000", {"list_price": 440000, "months_remaining": 5000}, "400 out_of_range months_remaining"),
    ("months_remaining 2**31", {"list_price": 440000, "months_remaining": 2 ** 31}, "400 out_of_range months_remaining"),
    ("balloon item 6.5", {**MINIMAL, "balloon_months": [6, 6.5]}, "400 wrong_type balloon_months[1]"),
    ('balloon item "12"', {**MINIMAL, "balloon_months": [6, "12"]}, "400 wrong_type balloon_months[1]"),
    ("balloon item null", {**MINIMAL, "balloon_months": [6, None]}, "400 null_not_allowed balloon_months[1]"),
    ("omitted defaults", dict(MINIMAL), "accepted; down_payment_pct resolves to 20.0"),
    ("the RA example", RA, "accepted"),
]


def parse(body):
    """The proto3 JSON mapping + resolve; (True, message) or (False, error text)."""
    try:
        return True, resolve(json_format.ParseDict(body, pb.SimulationInput(), ignore_unknown_fields=False))
    except Exception as exc:                      # ParseError, ValueError, OverflowError
        return False, f"{type(exc).__name__}: {str(exc)[:110]}"


def layer(body):
    try:
        simulation_input(body)
        return "accepted"
    except ApiError as exc:
        d = exc.to_dict()
        return f"{exc.status} {d['code']} {d.get('field', '')}".rstrip()


def to_json(msg) -> str:
    return json.dumps(json_format.MessageToDict(msg, preserving_proto_field_name=True))


def main():
    print("=== the .proto, read through the custom option ===")
    for i in FIELDS:
        print(f"  {i['name']:<24} {i['group']:<12} "
              f"{'required' if i['required'] else 'nullable' if i['nullable'] else 'default ' + json.dumps(i['default'])}")
    print("\n=== POST /api/simulations — proto3 JSON mapping (python protobuf) vs the contract vs the layer ===\n")
    for label, body, contract in CASES:
        ok, result = parse(body)
        print(f"# {label}\n  contract : {contract}\n  protobuf : {'accepted -> ' + to_json(result) if ok else result}"
              f"\n  layer    : {layer(body)}\n")
    print("=== nested: POST /api/comparisons ===")
    cmp = json_format.ParseDict({"base": {"fgts_upfront": 13000},
                                 "candidates": [MINIMAL, {"list_price": 396000, "months_remaining": "19"}]}, pb.ComparisonRequest())
    print("  candidate[1].months_remaining as a string:", cmp.candidates[1].months_remaining, "(accepted, coerced)")
    ra = parse(RA)[1]
    print("\n=== the RA input as the three DTOs ===\n ", json.dumps(split(ra)))
    print("  required down payment:", required_down_payment(ra), "remaining:", remaining_down_payment(ra))
    n = 20000
    t_pb = timeit.timeit(lambda: resolve(json_format.ParseDict(RA, pb.SimulationInput())), number=n) / n * 1e6
    t_layer = timeit.timeit(lambda: simulation_input(RA), number=n) / n * 1e6
    print(f"\n=== timing, the RA body, mean of {n}: ParseDict + resolve {t_pb:.1f} us · the shape layer {t_layer:.1f} us")


if __name__ == "__main__":
    main()
