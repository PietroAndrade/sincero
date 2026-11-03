"""
Small tests pinning the findings of docs/protobuf-languages.md for Python — the same seven as
../typescript/src/test.ts.

    cd backend && .venv/bin/python -m pytest ../docs/experiments/protobuf-languages/python -q -p no:cacheprovider
"""
import math

import pytest
from google.protobuf import json_format

from _setup import pb
from experiment import DEFAULT_NAME, FIELDS, RA, parse, remaining_down_payment, required_down_payment, resolve, split
from rules import violations


def test_the_generated_message_is_not_a_dto_but_carries_presence_and_the_amounts_follow():
    ra = json_format.ParseDict(RA, pb.SimulationInput())
    assert ra.list_price == 440000 and ra.HasField("developer_installment")
    assert not ra.HasField("incc_rate_pa")                       # `optional` + omitted: absent, not 0
    assert list(ra.balloon_months) == [6, 12]
    assert required_down_payment(resolve(ra)) == 88000 and remaining_down_payment(resolve(ra)) == 75000
    with pytest.raises(TypeError):
        hash(ra)                                                # mutable, unhashable: why the application generates dataclasses
    ra.list_price = 1                                           # and mutable


def test_the_proto_defaults_groups_and_nullability_are_readable_from_the_option():
    by_name = {f["name"]: f for f in FIELDS}
    assert len(FIELDS) == 16
    assert by_name["down_payment_pct"]["default"] == 20.0 and by_name["term_months"]["default"] == 360
    assert by_name["developer_installment"]["nullable"] and by_name["list_price"]["required"]
    assert list(split(resolve(json_format.ParseDict(RA, pb.SimulationInput())))) == ["contract", "market", "bank_credit"]


def test_resolve_applies_the_defaults_and_reports_missing_required_fields():
    ok, r = parse({"list_price": 440000, "months_remaining": 19})
    assert ok and (r.down_payment_pct, r.incc_rate_pa, r.name) == (20.0, 7.0, DEFAULT_NAME)
    assert not r.HasField("developer_installment")              # nullable stays absent
    assert parse({"list_price": 440000}) == (False, "ValueError: months_remaining is required")
    assert parse({"list_price": 0, "months_remaining": 19})[1].endswith("list_price is required")   # implicit presence


@pytest.mark.parametrize("body", [
    [1, 2], {"list_price": 440000, "months_remaining": 19.5}, {"list_price": 440000, "months_remaining": True},
    {"list_price": 440000, "months_remaining": 19, "foo": 1}, {"list_price": 440000, "months_remaining": 2 ** 31},
    {"list_price": math.nan, "months_remaining": 19}, {"list_price": 440000, "months_remaining": 19, "balloon_months": [6, 6.5]},
    {"list_price": 440000, "months_remaining": 19, "balloon_months": [6, None]},
])
def test_proto3_json_refuses_what_the_contract_refuses(body):
    assert parse(body)[0] is False


def test_proto3_json_accepts_what_the_contract_refuses():
    def accepted(body):
        ok, msg = parse(body)
        assert ok, msg
        return msg
    assert accepted({"list_price": "440000", "months_remaining": 19}).list_price == 440000         # strings are numbers
    assert accepted({"list_price": True, "months_remaining": 19}).list_price == 1.0                # a boolean is 1.0 (python only)
    assert accepted({"list_price": 440000, "months_remaining": "19"}).months_remaining == 19
    assert accepted({"listPrice": 440000, "monthsRemaining": 19}).list_price == 440000             # camelCase alias
    assert accepted({"list_price": 440000, "months_remaining": 19, "itbi_pct": None}).itbi_pct == 2.0   # null = unset = default
    assert math.isnan(accepted({"list_price": "NaN", "months_remaining": 19}).list_price)          # the quoted NaN
    assert accepted({"list_price": 440000, "months_remaining": 5000}).months_remaining == 5000     # no API limits
    assert list(accepted({"list_price": 440000, "months_remaining": 19, "balloon_months": [6, "12"]}).balloon_months) == [6, 12]


def test_a_huge_integer_is_a_python_exception_not_a_parse_error():
    assert parse({"list_price": 10 ** 400, "months_remaining": 19})[1].startswith("OverflowError")


def test_the_wire_stays_snake_case():
    msg = resolve(json_format.ParseDict(RA, pb.SimulationInput()))
    assert list(json_format.MessageToDict(msg, preserving_proto_field_name=True))[:3] == ["name", "list_price", "months_remaining"]
    assert list(json_format.MessageToDict(msg))[1] == "listPrice"                                  # the default


def test_validation_rules_declared_in_the_proto_are_enforced():
    assert violations(list_price=440000, months_remaining=19, fgts_upfront=13000, balloon_months=[6, 12]) == []
    assert violations(list_price=0, months_remaining=0) == [
        "list_price: must be greater than 0",
        "months_remaining: must be greater than or equal to 1 and less than or equal to 600"]
    assert violations(list_price=440000, months_remaining=19, fgts_upfront=300000, cash_upfront=140001) == \
        ["(message): upfront payments exceed the list price"]
    assert violations(list_price=440000, months_remaining=19, balloon_months=[6, 6, 0]) == [
        "balloon_months: repeated value must contain unique items", "balloon_months.[2]: must be greater than or equal to 1"]
