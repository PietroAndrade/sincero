"""
Small tests pinning the findings of docs/protobuf-languages.md for Python — the same seven as
../typescript/src/test.ts — and the evidence of docs/decisions/required-fields-explicit-presence.md
(required fields are `optional` + `required`; the rules refuse an absent or zero field before the model).

    cd backend && .venv/bin/python -m pytest ../docs/experiments/protobuf-languages/python -q -p no:cacheprovider
"""
import math

import pytest
from google.protobuf import json_format

from _setup import pb, presence_pb, rules_pb
from experiment import DEFAULT_NAME, FIELDS, RA, parse, remaining_down_payment, required_down_payment, resolve, split
from presence import outcome
from rules import simulate_if_valid, violations, violations_of_body


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
    assert parse({"list_price": 0, "months_remaining": 19})[0]  # explicit presence: a present 0 is not "missing" (the range rule refuses it)


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


# ----- required fields: `optional` + `required` (docs/decisions/required-fields-explicit-presence.md) -----
def test_a_required_field_absent_is_refused_as_required_and_zero_as_out_of_range():
    assert violations_of_body({}) == ["list_price: value is required", "months_remaining: value is required"]
    assert violations_of_body({"list_price": 440000, "months_remaining": None}) == ["months_remaining: value is required"]
    assert violations_of_body({"list_price": 440000, "months_remaining": 0}) == [
        "months_remaining: must be greater than or equal to 1 and less than or equal to 600"]
    assert violations_of_body({"list_price": 0, "months_remaining": 19}) == ["list_price: must be greater than 0"]
    assert violations_of_body({"months_remaining": 19, "fgts_upfront": 13000}) == ["list_price: value is required"]  # CEL quiet
    zero = rules_pb.ValidatedInput(list_price=440000, months_remaining=0)
    assert rules_pb.ValidatedInput.FromString(zero.SerializeToString()).HasField("months_remaining")  # 0 survives the wire


ABSENT_OR_ZERO = [
    {}, {"list_price": 440000}, {"months_remaining": 19},
    {"list_price": 440000, "months_remaining": 0}, {"list_price": 0, "months_remaining": 19},
    {"list_price": 0, "months_remaining": 0}, {"list_price": 440000, "months_remaining": 0.0},
    {"list_price": 440000, "months_remaining": None}, {"list_price": None, "months_remaining": 19},
]


@pytest.fixture
def model_runs(monkeypatch):
    """Every entry into the model's calculations (`OffPlanSimulator.run`, where all components are built)."""
    import app.models.simulator as simulator
    runs, real = [], simulator.OffPlanSimulator.run
    monkeypatch.setattr(simulator.OffPlanSimulator, "run", lambda self: runs.append(1) or real(self))
    return runs


@pytest.mark.parametrize("body", ABSENT_OR_ZERO)
def test_the_rules_refuse_an_absent_or_zero_required_field_before_the_model_runs(body, model_runs):
    refused = simulate_if_valid(body)
    assert isinstance(refused, list) and refused                # violations of the .proto's rules
    assert model_runs == []                                     # the model never ran


def test_a_body_the_rules_accept_reaches_the_model(model_runs):
    result = simulate_if_valid({"list_price": 440000, "months_remaining": 19})
    assert model_runs == [1] and result.input.contract.months_remaining == 19


def test_only_optional_plus_required_tells_absent_from_zero():
    required, out_of_range = "refused: value is required", "refused: must be greater than or equal to 1 and less than or equal to 600"
    absent, zero = {}, {"months_remaining": 0}
    assert outcome(presence_pb.A_PlainRejectZero, absent) == outcome(presence_pb.A_PlainRejectZero, zero) == out_of_range
    assert outcome(presence_pb.B_PlainRequired, absent) == outcome(presence_pb.B_PlainRequired, zero) == required
    assert outcome(presence_pb.C_OptionalOnly, absent) == "accepted"                 # the trap: optional alone
    assert outcome(presence_pb.D_OptionalRequired, absent) == required
    assert outcome(presence_pb.D_OptionalRequired, zero) == out_of_range
    assert outcome(presence_pb.F_PlainZeroIsValid, {}) == "accepted"                 # a plain field whose 0 is valid
    assert outcome(presence_pb.G_OptionalRequiredZeroIsValid, {}) == required
    assert outcome(presence_pb.G_OptionalRequiredZeroIsValid, {"amount": 0}) == "accepted"
