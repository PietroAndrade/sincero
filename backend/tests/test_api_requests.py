"""
The API's shape layer (docs/api-contract.md): every `400` rule with its `code`, `field` and
`index`, the order of checks, the `422` pass, and the normalised inputs the layer hands on.
"""
import math

import pytest

from app.controllers.api_requests import (FIELD_SPECS, MAX_ITEMS, UPPER_BOUNDS, ApiError, cash_ladder_amounts,
                                          cash_ladder_inputs, comparison_inputs, field_specs, simulate_all,
                                          simulate_one, simulation_input, what_if_inputs)
from app.models import ContractData, SimulationInput, field_names, simulate
from app.views import input_from_dict, input_to_dict, summary_to_dict, what_if_to_dict
from app.models import cash_ladder

RA = {"name": "RA", "list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000,
      "developer_installment": 2500, "balloon_months": [6, 12]}
MINIMAL = {"list_price": 440000, "months_remaining": 19}


def rejects(fn, *args, status=400, code, field=None, index=None, message=None) -> ApiError:
    with pytest.raises(ApiError) as info:
        fn(*args)
    err = info.value
    body = err.to_dict()
    assert (err.status, body["code"]) == (status, code), body
    assert body.get("field") == field, body
    assert body.get("index") == index, body
    if message:
        assert message in body["error"], body
    assert set(body) <= {"error", "code", "field", "index"}
    return err


@pytest.fixture
def base() -> SimulationInput:
    return simulation_input({"list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000})


# ----- GET /api/fields: specs come from the DTOs -----------------------------------------
def test_field_specs_cover_every_model_field_in_dto_order():
    assert [s["name"] for s in field_specs()] == list(field_names())


def test_field_specs_match_the_contract_table():
    by_name = {s["name"]: s for s in field_specs()}
    assert by_name["name"] == {"name": "name", "group": "contract", "type": "string", "required": False, "default": "CUSTOM", "unit": None}
    assert by_name["list_price"] == {"name": "list_price", "group": "contract", "type": "number", "required": True, "default": None, "unit": "R$"}
    assert by_name["months_remaining"]["type"] == "integer" and by_name["months_remaining"]["required"]
    assert by_name["developer_installment"]["type"] == "number|null"
    assert by_name["pre_approved_credit"] == {"name": "pre_approved_credit", "group": "bank_credit", "type": "number|null", "required": False, "default": None, "unit": "R$"}
    assert by_name["balloon_months"]["type"] == "integer[]" and by_name["balloon_months"]["default"] == []
    assert by_name["incc_rate_pa"] == {"name": "incc_rate_pa", "group": "market", "type": "number", "required": False, "default": 7.0, "unit": "% per year"}
    assert [s["name"] for s in field_specs() if s["required"]] == ["list_price", "months_remaining"]


def test_every_numeric_field_has_an_api_ceiling_or_a_model_bound():
    numeric = {s.name for s in FIELD_SPECS if s.kind in ("number", "integer")}
    assert numeric - set(UPPER_BOUNDS) == {"income_commitment_ratio"}, "a new numeric field needs an API limit"


# ----- POST /api/simulations: the resolved input ------------------------------------------
def test_resolved_input_applies_defaults_and_normalises_numbers():
    inp = simulation_input({"list_price": 440000, "months_remaining": 19.0, "developer_installment": 2500})
    assert inp == SimulationInput(ContractData("CUSTOM", 440000.0, 19, developer_installment=2500.0))
    assert isinstance(inp.contract.months_remaining, int) and isinstance(inp.contract.list_price, float)
    assert simulation_input({"list_price": 440000, "months_remaining": 19}) == simulation_input({"list_price": 440000.0, "months_remaining": 19.0})


def test_resolved_input_keeps_balloon_months_as_given_and_null_as_absent():
    inp = simulation_input({**RA, "developer_installment": None, "pre_approved_credit": None, "balloon_months": [12.0, 6]})
    assert inp.contract.balloon_months == (12, 6)
    assert inp.contract.developer_installment is None and inp.bank_credit.pre_approved_credit is None
    assert input_to_dict(inp)["name"] == "RA"


# ----- why the layer exists ------------------------------------------------------------------------
@pytest.mark.parametrize("body, without_the_layer, field", [
    ({"name": "RA", "list_price": "440000", "months_remaining": 19}, "crashes", "list_price"),        # a string for a number
    ({"name": "RA", "list_price": 440000, "months_remaining": 19.5}, "crashes", "months_remaining"),  # a fraction of a month
    ({"name": "RA", "list_price": 440000, "months_remaining": True}, "runs", "months_remaining"),     # a boolean — an int to Python
])
def test_input_from_dict_alone_lets_the_body_through_but_the_layer_rejects_it(body, without_the_layer, field):
    inp = input_from_dict(body)                               # the view builds the DTOs without looking at the values
    assert inp.contract.months_remaining == body["months_remaining"]
    if without_the_layer == "crashes":
        with pytest.raises(TypeError):                        # not a SimulationError: the model has no 422 for it
            simulate(inp)
    else:
        assert len(simulate(inp).timeline.months) == 1 + 1 + 360    # silently a 1-month contract
    rejects(simulation_input, body, code="wrong_type", field=field)   # the layer stops it at the door, as a 400


# ----- the 400 rules, one per code ---------------------------------------------------------------
@pytest.mark.parametrize("body", [[1, 2], 42, "x", None, True])
def test_body_must_be_an_object(body):
    rejects(simulation_input, body, code="wrong_type", field="body", message="request body must be a JSON object")


def test_required_fields():
    rejects(simulation_input, {"list_price": 440000}, code="missing_field", field="months_remaining", message="months_remaining is required")
    rejects(simulation_input, {"months_remaining": 19}, code="missing_field", field="list_price")
    rejects(simulation_input, {}, code="missing_field", field="list_price")


def test_unknown_fields_name_the_first_and_list_all_in_document_order():
    err = rejects(simulation_input, {**MINIMAL, "fgts_upfrnt": 13000, "foo": 1}, code="unknown_field", field="fgts_upfrnt")
    assert err.message == "unknown simulation input field(s): fgts_upfrnt, foo"


@pytest.mark.parametrize("field, value, got", [
    ("list_price", "440000", "a string"),
    ("list_price", True, "a boolean"),
    ("list_price", [440000], "an array"),
    ("months_remaining", 19.5, "19.5"),
    ("months_remaining", "19", "a string"),
    ("months_remaining", False, "a boolean"),
    ("name", 7, "a number"),
    ("balloon_months", 6, "a number"),
    ("balloon_months", {"6": 1}, "an object"),
    ("developer_installment", "2500", "a string"),
    ("pro_soluto_months", 12.25, "12.25"),
])
def test_strict_json_types(field, value, got):
    rejects(simulation_input, {**MINIMAL, field: value}, code="wrong_type", field=field, message=f"got {got}")


def test_integers_accept_a_number_without_fractional_part():
    assert simulation_input({**MINIMAL, "term_months": 240.0}).market.term_months == 240


def test_balloon_months_items_are_checked_one_by_one():
    rejects(simulation_input, {**MINIMAL, "balloon_months": [6, 6.5]}, code="wrong_type", field="balloon_months[1]")
    rejects(simulation_input, {**MINIMAL, "balloon_months": [6, "12"]}, code="wrong_type", field="balloon_months[1]")
    rejects(simulation_input, {**MINIMAL, "balloon_months": [None]}, code="null_not_allowed", field="balloon_months[0]")
    rejects(simulation_input, {**MINIMAL, "balloon_months": [6, math.nan]}, code="not_finite", field="balloon_months[1]")
    rejects(simulation_input, {**MINIMAL, "balloon_months": list(range(1, 62))}, code="out_of_range", field="balloon_months",
            message="at most 60 items")


@pytest.mark.parametrize("field", ["name", "list_price", "months_remaining", "balloon_months", "itbi_pct", "term_months"])
def test_null_is_rejected_where_the_table_does_not_say_or_null(field):
    rejects(simulation_input, {**MINIMAL, field: None}, code="null_not_allowed", field=field,
            message=f"{field} must not be null; omit it to use the default")


def test_null_means_absent_on_the_two_nullable_fields():
    inp = simulation_input({**MINIMAL, "developer_installment": None, "pre_approved_credit": None})
    assert inp.contract.developer_installment is None and inp.bank_credit.pre_approved_credit is None


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, 10**400])
@pytest.mark.parametrize("field", ["list_price", "income_commitment_ratio", "developer_installment"])
def test_numbers_must_be_finite(field, value):
    rejects(simulation_input, {**MINIMAL, field: value}, code="not_finite", field=field, message="finite number")


@pytest.mark.parametrize("field, value", [
    ("months_remaining", 601), ("months_remaining", 5000), ("term_months", 10**400), ("pro_soluto_months", 1e20),
    ("list_price", 10**12 + 1), ("fgts_upfront", 1e13), ("cash_upfront", 2e12), ("developer_installment", 1e13),
    ("pre_approved_credit", 1e13), ("down_payment_pct", 1001), ("itbi_pct", 1e4), ("registry_pct", 1e4),
    ("incc_rate_pa", 1000.5), ("bank_rate_pa", 1e6),
])
def test_api_limits(field, value):
    rejects(simulation_input, {**MINIMAL, field: value}, code="out_of_range", field=field, message="must be at most")


def test_limits_are_inclusive_and_lower_bounds_are_left_to_the_model():
    inp = simulation_input({**MINIMAL, "months_remaining": 600, "list_price": 10**12, "incc_rate_pa": 1000, "term_months": 600})
    assert inp.contract.months_remaining == 600
    assert simulation_input({**MINIMAL, "list_price": -1}).contract.list_price == -1   # 422, not 400
    rejects(simulate_one, simulation_input({**MINIMAL, "list_price": -1}), status=422, code="invalid_input",
            message="list price must be greater than zero")


# ----- the order of checks ------------------------------------------------------------------------
def test_unknown_keys_come_before_required_keys():
    rejects(simulation_input, {"foo": 1}, code="unknown_field", field="foo")


def test_required_keys_come_before_field_checks():
    rejects(simulation_input, {"list_price": "x"}, code="missing_field", field="months_remaining")


def test_fields_are_checked_in_dto_order():
    rejects(simulation_input, {"months_remaining": 19.5, "list_price": "x"}, code="wrong_type", field="list_price")
    rejects(simulation_input, {**MINIMAL, "pro_soluto_months": None, "incc_rate_pa": "7"}, code="wrong_type", field="incc_rate_pa")


def test_within_a_field_null_then_type_then_finite_then_limit():
    rejects(simulation_input, {**MINIMAL, "itbi_pct": None}, code="null_not_allowed", field="itbi_pct")
    rejects(simulation_input, {**MINIMAL, "itbi_pct": "1e400"}, code="wrong_type", field="itbi_pct")
    rejects(simulation_input, {**MINIMAL, "itbi_pct": math.inf}, code="not_finite", field="itbi_pct")
    rejects(simulation_input, {**MINIMAL, "itbi_pct": 1e300}, code="out_of_range", field="itbi_pct")


def test_shape_errors_come_before_model_errors():
    # months_remaining = 0 is a 422, but the unknown key is seen first
    rejects(simulation_input, {"list_price": 440000, "months_remaining": 0, "foo": 1}, code="unknown_field", field="foo")


# ----- the 422 pass ----------------------------------------------------------------------------------
def test_model_errors_are_422_with_the_message_verbatim_and_no_field():
    err = rejects(simulate_one, simulation_input({**MINIMAL, "months_remaining": 0}), status=422, code="invalid_input")
    assert err.to_dict() == {"error": "months remaining until delivery must be at least 1", "code": "invalid_input"}


def test_balloon_sizing_errors_surface_at_creation():
    inp = simulation_input({**MINIMAL, "developer_installment": 1900, "balloon_months": []})
    rejects(simulate_one, inp, status=422, code="invalid_input", message="do not cover the down payment balance")


def test_simulate_one_returns_the_same_result_as_the_model():
    inp = simulation_input(RA)
    assert summary_to_dict(simulate_one(inp)) == summary_to_dict(simulate(inp))


# ----- POST /api/comparisons ----------------------------------------------------------------------
REFERENCE = {"base": {"fgts_upfront": 13000},
             "candidates": [{"name": "SO", "list_price": 300000, "months_remaining": 4},
                            {"name": "F", "list_price": 396000, "months_remaining": 8},
                            {"name": "SV", "list_price": 233000, "months_remaining": 17},
                            {"name": "F4", "list_price": 320400, "months_remaining": 19},
                            {"name": "RA", "list_price": 440000, "months_remaining": 19}]}


def test_comparison_merges_base_into_every_candidate_in_order():
    inputs = comparison_inputs(REFERENCE)
    assert [i.contract.name for i in inputs] == ["SO", "F", "SV", "F4", "RA"]
    assert all(i.contract.fgts_upfront == 13000.0 for i in inputs)
    assert inputs[-1] == SimulationInput(ContractData("RA", 440000, 19, fgts_upfront=13000))
    assert [summary_to_dict(r)["name"] for r in simulate_all(inputs)] == ["SO", "F", "SV", "F4", "RA"]


def test_candidate_overrides_base():
    [inp] = comparison_inputs({"base": {**MINIMAL, "incc_rate_pa": 7}, "candidates": [{"incc_rate_pa": 4}]})
    assert inp.market.incc_rate_pa == 4.0


def test_comparison_candidates_are_the_same_inputs_as_individual_posts():
    assert comparison_inputs(REFERENCE) == [simulation_input({**REFERENCE["base"], **c}) for c in REFERENCE["candidates"]]


def test_comparison_base_is_optional():
    assert comparison_inputs({"candidates": [MINIMAL]}) == [simulation_input(MINIMAL)]


def test_comparison_wrapper_rules():
    rejects(comparison_inputs, [MINIMAL], code="wrong_type", field="body")
    rejects(comparison_inputs, {"base": {}}, code="missing_field", field="candidates", message="candidates is required")
    rejects(comparison_inputs, {"candidates": None}, code="null_not_allowed", field="candidates")
    rejects(comparison_inputs, {"candidates": {}}, code="wrong_type", field="candidates")
    rejects(comparison_inputs, {"candidates": MINIMAL}, code="wrong_type", field="candidates")
    rejects(comparison_inputs, {"candidates": []}, code="out_of_range", field="candidates",
            message="candidates must have between 1 and 20 items")
    rejects(comparison_inputs, {"candidates": [MINIMAL] * (MAX_ITEMS + 1)}, code="out_of_range", field="candidates")
    rejects(comparison_inputs, {"base": None, "candidates": [MINIMAL]}, code="null_not_allowed", field="base")
    rejects(comparison_inputs, {"base": [], "candidates": [MINIMAL]}, code="wrong_type", field="base")
    rejects(comparison_inputs, {"candidates": [MINIMAL], "foo": 1}, code="unknown_field", field="foo")
    assert len(comparison_inputs({"candidates": [MINIMAL] * MAX_ITEMS})) == MAX_ITEMS


def test_comparison_errors_name_base_without_index():
    err = rejects(comparison_inputs, {"base": {"fgts": 13000}, "candidates": [MINIMAL]}, code="unknown_field", field="base.fgts")
    assert err.message == "unknown simulation input field(s) in base: fgts"
    rejects(comparison_inputs, {"base": {"fgts_upfront": "13000"}, "candidates": [MINIMAL]}, code="wrong_type", field="base.fgts_upfront")
    rejects(comparison_inputs, {"base": {"itbi_pct": None}, "candidates": [MINIMAL]}, code="null_not_allowed", field="base.itbi_pct")


def test_comparison_errors_name_the_candidate_with_index():
    err = rejects(comparison_inputs, {"candidates": [{"name": "SO", "list_price": 300000}]},
                  code="missing_field", field="candidates[0].months_remaining", index=0)
    assert err.message == "candidates[0].months_remaining is required"
    rejects(comparison_inputs, {"candidates": [MINIMAL, {**MINIMAL, "months_remaining": "19"}]},
            code="wrong_type", field="candidates[1].months_remaining", index=1, message="candidates[1].months_remaining must be an integer")
    rejects(comparison_inputs, {"candidates": [MINIMAL, {**MINIMAL, "foo": 1}]},
            code="unknown_field", field="candidates[1].foo", index=1, message="in candidates[1]: foo")
    rejects(comparison_inputs, {"candidates": [MINIMAL, 5]}, code="invalid_value", field="candidates[1]", index=1)
    rejects(comparison_inputs, {"candidates": [MINIMAL, None]}, code="null_not_allowed", field="candidates[1]", index=1,
            message="candidates[1] must not be null")
    rejects(comparison_inputs, {"candidates": [MINIMAL, {**MINIMAL, "list_price": math.nan}]},
            code="not_finite", field="candidates[1].list_price", index=1)
    rejects(comparison_inputs, {"candidates": [MINIMAL, {**MINIMAL, "term_months": 601}]},
            code="out_of_range", field="candidates[1].term_months", index=1)


def test_comparison_required_fields_are_satisfied_by_base_or_candidate():
    assert comparison_inputs({"base": {"list_price": 1}, "candidates": [{"months_remaining": 1}]})
    assert comparison_inputs({"base": MINIMAL, "candidates": [{"name": "A"}]})
    rejects(comparison_inputs, {"base": {"list_price": 1}, "candidates": [{"name": "A"}]},
            code="missing_field", field="candidates[0].months_remaining", index=0)


def test_comparison_first_bad_candidate_wins_and_nothing_is_simulated():
    body = {"candidates": [MINIMAL, {"list_price": 1}, {"list_price": "x", "months_remaining": 1}]}
    rejects(comparison_inputs, body, code="missing_field", field="candidates[1].months_remaining", index=1)


def test_comparison_model_errors_carry_the_index():
    body = {"base": {"fgts_upfront": 13000},
            "candidates": [{"name": "SO", "list_price": 300000, "months_remaining": 4},
                           {"name": "F", "list_price": 396000, "months_remaining": 0}]}
    err = rejects(simulate_all, comparison_inputs(body), status=422, code="invalid_input", index=1)
    assert err.to_dict() == {"error": "months remaining until delivery must be at least 1", "code": "invalid_input", "index": 1}


# ----- POST /api/simulations/{id}/what-if --------------------------------------------------------------
def test_what_if_variations_are_the_base_with_overrides(base):
    inputs = what_if_inputs({"variations": [{"incc_rate_pa": 4.0}, {"cash_upfront": 30000}, {"cash_upfront": 30000, "incc_rate_pa": 4.0}]}, base)
    assert inputs == [base.with_overrides(incc_rate_pa=4.0), base.with_overrides(cash_upfront=30000.0),
                      base.with_overrides(cash_upfront=30000.0, incc_rate_pa=4.0)]


def test_what_if_no_op_variation_is_valid_and_equals_the_base(base):
    [same] = what_if_inputs({"variations": [{"cash_upfront": 0}]}, base)
    assert same == base


def test_what_if_null_is_a_meaningful_override_on_the_nullable_fields():
    base = simulation_input(RA)
    [inp] = what_if_inputs({"variations": [{"developer_installment": None, "balloon_months": []}]}, base)
    assert inp.contract.developer_installment is None and inp.contract.balloon_months == ()


def test_what_if_wrapper_rules(base):
    rejects(what_if_inputs, [], base, code="wrong_type", field="body")
    rejects(what_if_inputs, {}, base, code="missing_field", field="variations")
    rejects(what_if_inputs, {"variations": None}, base, code="null_not_allowed", field="variations")
    rejects(what_if_inputs, {"variations": {"incc_rate_pa": 4}}, base, code="wrong_type", field="variations")
    rejects(what_if_inputs, {"variations": []}, base, code="out_of_range", field="variations")
    rejects(what_if_inputs, {"variations": [{"incc_rate_pa": 4}] * 21}, base, code="out_of_range", field="variations")
    rejects(what_if_inputs, {"variations": [{"incc_rate_pa": 4}], "base": {}}, base, code="unknown_field", field="base")


def test_what_if_item_rules(base):
    err = rejects(what_if_inputs, {"variations": [{"incc": 4.0}]}, base, code="unknown_field", field="variations[0].incc", index=0)
    assert err.message == "unknown simulation input field(s) in variations[0]: incc"
    err = rejects(what_if_inputs, {"variations": [{"incc_rate_pa": 4.0}, {}]}, base, code="invalid_value", field="variations[1]", index=1)
    assert err.message == "variations[1] is empty"
    rejects(what_if_inputs, {"variations": [{"incc_rate_pa": 4.0}, 4.0]}, base, code="invalid_value", field="variations[1]", index=1)
    rejects(what_if_inputs, {"variations": [None]}, base, code="null_not_allowed", field="variations[0]", index=0)
    rejects(what_if_inputs, {"variations": [{"itbi_pct": None}]}, base, code="null_not_allowed", field="variations[0].itbi_pct", index=0)
    rejects(what_if_inputs, {"variations": [{"months_remaining": 19.5}]}, base, code="wrong_type", field="variations[0].months_remaining", index=0)
    rejects(what_if_inputs, {"variations": [{"cash_upfront": math.inf}]}, base, code="not_finite", field="variations[0].cash_upfront", index=0)
    rejects(what_if_inputs, {"variations": [{"term_months": 601}]}, base, code="out_of_range", field="variations[0].term_months", index=0)


def test_what_if_does_not_require_list_price_or_months(base):
    assert what_if_inputs({"variations": [{"name": "RA bis"}]}, base)[0].contract.name == "RA bis"


def test_what_if_model_errors_carry_the_index(base):
    inputs = what_if_inputs({"variations": [{"incc_rate_pa": 4.0}, {"incc_rate_pa": -150}]}, base)
    err = rejects(simulate_all, inputs, status=422, code="invalid_input", index=1)
    assert err.message == "INCC rate must be greater than -100% per year"


# ----- POST /api/simulations/{id}/cash-ladder --------------------------------------------------------
def test_ladder_amounts_are_floats_in_order():
    assert cash_ladder_amounts({"amounts": [0, 30000, 75000.0, 100000]}) == [0.0, 30000.0, 75000.0, 100000.0]


def test_ladder_rungs_equal_the_same_amounts_as_what_if_variations(base):
    amounts = [0, 30000, 75000, 100000]
    rungs = cash_ladder_inputs({"amounts": amounts}, base)
    assert rungs == what_if_inputs({"variations": [{"cash_upfront": a} for a in amounts]}, base)
    assert rungs[0] == base                                        # the first rung collapses onto the base


def test_ladder_reproduces_the_models_cash_ladder(base):
    amounts = [0, 30000, 75000, 100000]
    rows = [summary_to_dict(r) for r in simulate_all(cash_ladder_inputs({"amounts": amounts}, base))]
    expected = [s["summary"] for s in what_if_to_dict(cash_ladder(base, amounts))["scenarios"]]
    assert rows == expected
    assert [r["developer_installment"] for r in rows][2:] == [0.0, 0.0]
    assert rows[3]["hidden_incc_debt"] < rows[2]["hidden_incc_debt"] == rows[0]["hidden_incc_debt"]


def test_ladder_wrapper_rules():
    rejects(cash_ladder_amounts, [0, 1], code="wrong_type", field="body")
    rejects(cash_ladder_amounts, {}, code="missing_field", field="amounts")
    rejects(cash_ladder_amounts, {"amounts": None}, code="null_not_allowed", field="amounts")
    rejects(cash_ladder_amounts, {"amounts": 30000}, code="wrong_type", field="amounts")
    err = rejects(cash_ladder_amounts, {"amounts": []}, code="out_of_range", field="amounts")
    assert err.message == "amounts must have between 1 and 20 items"
    rejects(cash_ladder_amounts, {"amounts": list(range(21))}, code="out_of_range", field="amounts")
    rejects(cash_ladder_amounts, {"amounts": [0], "variations": []}, code="unknown_field", field="variations")


def test_ladder_item_rules():
    err = rejects(cash_ladder_amounts, {"amounts": [0, 30000, 30000]}, code="invalid_value", field="amounts[2]", index=2)
    assert err.message == "amounts must be strictly increasing: amounts[2] = 30000 is not greater than amounts[1]"
    rejects(cash_ladder_amounts, {"amounts": [30000, 0]}, code="invalid_value", field="amounts[1]", index=1)
    err = rejects(cash_ladder_amounts, {"amounts": [0, -1]}, code="out_of_range", field="amounts[1]", index=1)
    assert err.message == "amounts must not be negative: amounts[1] = -1"
    rejects(cash_ladder_amounts, {"amounts": [-1]}, code="out_of_range", field="amounts[0]", index=0)
    rejects(cash_ladder_amounts, {"amounts": [0, "30000"]}, code="wrong_type", field="amounts[1]", index=1)
    rejects(cash_ladder_amounts, {"amounts": [0, True]}, code="wrong_type", field="amounts[1]", index=1)
    err = rejects(cash_ladder_amounts, {"amounts": [0, None]}, code="null_not_allowed", field="amounts[1]", index=1)
    assert err.message == "amounts[1] must not be null"
    rejects(cash_ladder_amounts, {"amounts": [0, math.nan]}, code="not_finite", field="amounts[1]", index=1)
    rejects(cash_ladder_amounts, {"amounts": [0, 1e13]}, code="out_of_range", field="amounts[1]", index=1, message="at most")


def test_ladder_first_offending_amount_wins():
    rejects(cash_ladder_amounts, {"amounts": [0, -1, "x"]}, code="out_of_range", field="amounts[1]", index=1)
    rejects(cash_ladder_amounts, {"amounts": [0, "x", -1]}, code="wrong_type", field="amounts[1]", index=1)


def test_ladder_rung_above_the_list_price_is_422_with_index(base):
    err = rejects(simulate_all, cash_ladder_inputs({"amounts": [0, 500000]}, base), status=422, code="invalid_input", index=1)
    assert err.message == "upfront payments of R$ 513,000.00 exceed the list price of R$ 440,000.00"


# ----- the error body ----------------------------------------------------------------------------------------
def test_error_body_has_only_the_contract_keys_in_order():
    assert list(ApiError(400, "wrong_type", "m", field="f", index=1).to_dict()) == ["error", "code", "field", "index"]
    assert ApiError(422, "invalid_input", "m").to_dict() == {"error": "m", "code": "invalid_input"}
    assert ApiError(404, "not_found", "m", index=0).to_dict() == {"error": "m", "code": "not_found", "index": 0}
    assert str(ApiError(400, "wrong_type", "the message")) == "the message"
