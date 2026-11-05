"""
`SimulationOverrides` is `SimulationInput` with every field optional: same names, numbers, types
and `buf.validate` rules minus `required`, `balloon_months` as a `BalloonMonths` and the nullable
fields as a `NullableAmount` (proto/sincero/simulation_input.proto). These tests read the
descriptors of the generated code (`app/gen/`, `make proto`; `make proto-check` keeps it fresh)
and run `protovalidate` on the partial inputs of the requests that use it.
"""
import json
import re

import pytest

protovalidate = pytest.importorskip("protovalidate")
from protovalidate._gen.buf.validate.validate_pb import ext_field as rules_ext  # noqa: E402

from app.gen.sincero.simulation_input_pb import (BalloonMonths, NullableAmount, SimulationInput,  # noqa: E402
                                                 SimulationOverrides, ext_field as meta_ext)
from app.gen.sincero.simulations_service_pb import CreateComparisonRequest, CreateWhatIfRequest  # noqa: E402

INPUT = SimulationInput.desc().fields
OVERRIDES = SimulationOverrides.desc().fields
PAIRS = list(zip(INPUT, OVERRIDES))
WRAPPERS = {".sincero.BalloonMonths": BalloonMonths, ".sincero.NullableAmount": NullableAmount}


def rules(field) -> dict:
    options = field.proto.options                 # None when the field has no options at all
    return json.loads(options[rules_ext].to_json()) if options is not None and rules_ext in options else {}


def nullable(field) -> bool:
    options = field.proto.options
    return options is not None and meta_ext in options and options[meta_ext].nullable


def holder(field):
    """The field that holds the value: the field itself, or the one field of its wrapper."""
    wrapper = WRAPPERS.get(field.proto.type_name)
    return wrapper.desc().fields[0] if wrapper else field


# ----- the shape mirrors SimulationInput ------------------------------------------------------
def test_same_fields_same_numbers_same_order():
    assert [(f.name, f.number) for f in OVERRIDES] == [(f.name, f.number) for f in INPUT]


@pytest.mark.parametrize("inp, over", PAIRS, ids=[f.name for f, _ in PAIRS])
def test_every_field_has_presence_and_the_input_type(inp, over):
    if inp.proto.label.name == "REPEATED":
        assert over.proto.type_name == ".sincero.BalloonMonths"
    elif nullable(inp):
        assert over.proto.type_name == ".sincero.NullableAmount"
    else:
        assert over.proto.proto3_optional, f"{over.name} must be optional (explicit presence)"
    value = holder(over)
    assert (value.proto.type, value.proto.label) == (inp.proto.type, inp.proto.label)


@pytest.mark.parametrize("inp, over", PAIRS, ids=[f.name for f, _ in PAIRS])
def test_same_rules_minus_required(inp, over):
    expected = {k: v for k, v in rules(inp).items() if k != "required"}
    assert rules(holder(over)) == expected
    assert "required" not in rules(over)


def test_a_variation_is_not_empty_when_any_field_is_set():
    expression = rules(CreateWhatIfRequest.desc().fields[1])["repeated"]["items"]["cel"][0]["expression"]
    assert set(re.findall(r"has\(this\.(\w+)\)", expression)) == {f.name for f in OVERRIDES}


# ----- protovalidate on the partial inputs ------------------------------------------------------
def violations(message) -> set[str]:
    try:
        protovalidate.validate(message)
    except protovalidate.ValidationError as exc:
        return {v.proto.rule_id for v in exc.violations}
    return set()


@pytest.mark.parametrize("overrides, expected", [
    (SimulationOverrides(), set()),                                          # nothing set: valid
    (SimulationOverrides(incc_rate_pa=4.0), set()),
    (SimulationOverrides(list_price=0), {"double.gt"}),                      # validated when set...
    (SimulationOverrides(months_remaining=601), {"int32.gte_lte"}),
    (SimulationOverrides(list_price=440000, months_remaining=0), {"int32.gte_lte"}),
])
def test_overrides_are_validated_when_set_and_never_required(overrides, expected):
    assert violations(overrides) == expected


@pytest.mark.parametrize("request_, expected", [
    (CreateComparisonRequest(base=SimulationOverrides(list_price=440000),
                             candidates=[SimulationOverrides(months_remaining=19),
                                         SimulationOverrides(months_remaining=30, cash_upfront=30000)]), set()),
    (CreateComparisonRequest(candidates=[SimulationOverrides(list_price=440000, months_remaining=19)]), set()),
    (CreateComparisonRequest(candidates=[SimulationOverrides(months_remaining=19)]), {"candidates.list_price"}),
    (CreateComparisonRequest(base=SimulationOverrides(list_price=440000),
                             candidates=[SimulationOverrides(months_remaining=19), SimulationOverrides()]),
     {"candidates.months_remaining"}),
    (CreateComparisonRequest(base=SimulationOverrides(list_price=440000, months_remaining=19),
                             candidates=[SimulationOverrides(list_price=-1)]), {"double.gt"}),
    (CreateComparisonRequest(), {"repeated.min_items"}),
])
def test_comparison_candidates_get_the_required_fields_from_themselves_or_base(request_, expected):
    assert violations(request_) == expected


@pytest.mark.parametrize("variation, expected", [
    (SimulationOverrides(), {"variation.not_empty"}),
    (SimulationOverrides(incc_rate_pa=4.0), set()),
    (SimulationOverrides(balloon_months=BalloonMonths()), set()),            # clear the balloons
    (SimulationOverrides(developer_installment=NullableAmount()), set()),    # back to null
    (SimulationOverrides(name=""), set()),                                   # "" is set, not absent
    (SimulationOverrides(months_remaining=0), {"int32.gte_lte"}),
])
def test_what_if_variations(variation, expected):
    assert violations(CreateWhatIfRequest(id="56c8", variations=[variation])) == expected


def test_empty_and_null_are_values_on_the_wire():
    """JSON: `{}` sets the wrapper (no balloons / null); an omitted key keeps the base's value."""
    cleared = SimulationOverrides.from_json('{"balloon_months": {}, "developer_installment": {}}')
    assert cleared.has_field("balloon_months") and list(cleared.balloon_months.months) == []
    assert cleared.has_field("developer_installment") and not cleared.developer_installment.has_field("value")
    kept = SimulationOverrides.from_json('{"cash_upfront": 30000}')
    assert not kept.has_field("balloon_months") and not kept.has_field("developer_installment")
    set_ = SimulationOverrides.from_json('{"balloon_months": {"months": [6, 12]}, "developer_installment": {"value": 2500}}')
    assert list(set_.balloon_months.months) == [6, 12] and set_.developer_installment.value == 2500
