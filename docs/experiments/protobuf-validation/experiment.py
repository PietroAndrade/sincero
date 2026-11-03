"""
Experiment: validate the `POST /api/simulations` body with Protocol Buffers' proto3 JSON
mapping (`google.protobuf.json_format.ParseDict`) and compare, case by case, with what the
contract requires and what the hand-written layer (`app/controllers/api_requests.py`) answers.

Run from the repository root:

    python3 -m venv /tmp/pbenv && /tmp/pbenv/bin/pip install grpcio-tools
    cd docs/experiments/protobuf-validation
    /tmp/pbenv/bin/python -m grpc_tools.protoc -I. --python_out=. simulation_input.proto
    PYTHONPATH=../../../backend /tmp/pbenv/bin/python experiment.py

Results are recorded in docs/json-validation-tools.md.
"""
from __future__ import annotations

import json
import math
import sys
import timeit

from google.protobuf import json_format

import simulation_input_pb2 as pb

sys.path.insert(0, "../../../backend")
from app.controllers.api_requests import ApiError, simulation_input  # noqa: E402

MINIMAL = {"list_price": 440000, "months_remaining": 19}

# (label, body, what the contract says)
CASES = [
    ("body is an array",            [1, 2],                                              "400 wrong_type body"),
    ("string for a number",         {"list_price": "440000", "months_remaining": 19},    "400 wrong_type list_price"),
    ("boolean for a number",        {"list_price": True, "months_remaining": 19},        "400 wrong_type list_price"),
    ("19.0 for an integer",         {"list_price": 440000, "months_remaining": 19.0},    "accepted (months_remaining = 19)"),
    ("19.5 for an integer",         {"list_price": 440000, "months_remaining": 19.5},    "400 wrong_type months_remaining"),
    ('"19" for an integer',         {"list_price": 440000, "months_remaining": "19"},    "400 wrong_type months_remaining"),
    ("true for an integer",         {"list_price": 440000, "months_remaining": True},    "400 wrong_type months_remaining"),
    ("two unknown fields",          {**MINIMAL, "fgts_upfrnt": 13000, "foo": 1},         "400 unknown_field fgts_upfrnt (message lists both)"),
    ("missing months_remaining",    {"list_price": 440000},                              "400 missing_field months_remaining"),
    ("null on itbi_pct",            {**MINIMAL, "itbi_pct": None},                       "400 null_not_allowed itbi_pct"),
    ("null on developer_installment", {**MINIMAL, "developer_installment": None},        "accepted (absent)"),
    ("NaN (parsed float)",          {"list_price": math.nan, "months_remaining": 19},    "400 not_finite list_price"),
    ('"NaN" (string)',              {"list_price": "NaN", "months_remaining": 19},       "400 wrong_type list_price"),
    ("Infinity",                    {"list_price": math.inf, "months_remaining": 19},    "400 not_finite list_price"),
    ("months_remaining 5000",       {"list_price": 440000, "months_remaining": 5000},    "400 out_of_range months_remaining"),
    ("list_price 10**400",          {"list_price": 10**400, "months_remaining": 19},     "400 not_finite list_price"),
    ("months_remaining 2**31",      {"list_price": 440000, "months_remaining": 2**31},   "400 out_of_range months_remaining"),
    ("balloon item 6.5",            {**MINIMAL, "balloon_months": [6, 6.5]},             "400 wrong_type balloon_months[1]"),
    ('balloon item "12"',           {**MINIMAL, "balloon_months": [6, "12"]},            "400 wrong_type balloon_months[1]"),
    ("balloon item null",           {**MINIMAL, "balloon_months": [6, None]},            "400 null_not_allowed balloon_months[1]"),
    ("61 balloon months",           {**MINIMAL, "balloon_months": list(range(1, 62))},   "400 out_of_range balloon_months"),
    ("omitted defaults",            dict(MINIMAL),                                       "accepted; down_payment_pct resolves to 20.0"),
    ("the RA example",              {"name": "RA", "list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000,
                                     "developer_installment": 2500, "balloon_months": [6, 12]}, "accepted"),
]

COMPARISON_CASES = [
    ("candidate[1] months is a string", {"base": {"fgts_upfront": 13000},
                                         "candidates": [MINIMAL, {"list_price": 396000, "months_remaining": "19"}]},
     "400 wrong_type candidates[1].months_remaining, index 1  (accepted by proto3: strings are numbers)"),
    ("candidate[1] has an unknown key", {"candidates": [MINIMAL, {**MINIMAL, "foo": 1}]},
     "400 unknown_field candidates[1].foo, index 1"),
    ("candidate[1] months 19.5", {"candidates": [MINIMAL, {**MINIMAL, "months_remaining": 19.5}]},
     "400 wrong_type candidates[1].months_remaining, index 1"),
    ("candidates is an object", {"candidates": {"list_price": 1}}, "400 wrong_type candidates"),
    ("candidates is empty", {"candidates": []}, "400 out_of_range candidates"),
]


def with_protobuf(body, message_type=pb.SimulationInput):
    msg = message_type()
    try:
        json_format.ParseDict(body, msg)
    except json_format.ParseError as exc:
        return f"ParseError: {exc}"
    except Exception as exc:                       # anything that is not the library's own error type
        return f"{type(exc).__name__}: {exc}"
    present = json_format.MessageToDict(msg, preserving_proto_field_name=True)   # only the fields that were set
    return f"accepted -> {json.dumps(present)}"


def with_layer(body):
    try:
        inp = simulation_input(body)
        return f"accepted -> months={inp.contract.months_remaining!r} list_price={inp.contract.list_price!r} dp%={inp.contract.down_payment_pct}"
    except ApiError as exc:
        d = exc.to_dict()
        return f"{exc.status} {d['code']} {d.get('field', '')}".rstrip()


def main() -> None:
    print("=== POST /api/simulations — proto3 JSON mapping vs the contract vs the layer ===\n")
    for label, body, contract in CASES:
        print(f"# {label}")
        print(f"  contract : {contract}")
        print(f"  protobuf : {with_protobuf(body)}")
        print(f"  layer    : {with_layer(body)}")
        print()

    print("=== POST /api/comparisons (nested: base + candidates) ===\n")
    for label, body, contract in COMPARISON_CASES:
        print(f"# {label}")
        print(f"  contract : {contract}")
        print(f"  protobuf : {with_protobuf(body, pb.ComparisonRequest)[:200]}")
        print()

    ra = CASES[-1][1]
    n = 5000
    t_pb = timeit.timeit(lambda: json_format.ParseDict(ra, pb.SimulationInput()), number=n) / n * 1e6
    t_layer = timeit.timeit(lambda: simulation_input(ra), number=n) / n * 1e6
    print(f"=== timing, the RA body, mean of {n} runs ===")
    print(f"  protobuf ParseDict : {t_pb:6.1f} us")
    print(f"  layer              : {t_layer:6.1f} us")


if __name__ == "__main__":
    main()
