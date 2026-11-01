"""The JSON view is the API/front-end contract: shape, round-trips and serialisability."""
import json

import pytest

from app.models import SimulationInput, cash_ladder, compare, simulate
from app.views import (comparison_to_dict, input_from_dict, input_to_dict, report, simulation_to_dict,
                       what_if_to_dict)


@pytest.fixture
def ra() -> SimulationInput:
    return SimulationInput("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500, balloon_months=(6, 12))


def test_input_round_trips_through_dict(ra):
    data = input_to_dict(ra)
    assert data["balloon_months"] == [6, 12]
    assert input_from_dict(data) == ra


def test_simulation_payload_shape_and_json(ra):
    payload = simulation_to_dict(simulate(ra))
    assert set(payload) == {"input", "rates", "down_payment", "mortgage", "construction_interest",
                            "closing_costs", "financing", "credit_gap", "total_cost", "timeline"}
    assert payload["total_cost"]["breakdown"][-1]["component"] == "Total"
    assert len(payload["timeline"]["months"]) == 1 + 19 + 360
    json.dumps(payload)


def test_comparison_rows_carry_names(ra):
    f = ra.with_overrides(name="F", list_price=396_000, months_remaining=8, balloon_months=(4,))
    rows = comparison_to_dict(compare([ra, f]))
    assert [r["name"] for r in rows] == ["RA", "F"]


def test_what_if_deltas_are_relative_to_base(ra):
    out = what_if_to_dict(cash_ladder(ra.with_overrides(developer_installment=None, balloon_months=()), [0, 30_000]))
    assert out["scenarios"][0]["delta"]["developer_installment"] == pytest.approx(0)
    assert out["scenarios"][1]["delta"]["developer_installment"] < 0
    assert out["scenarios"][1]["delta"]["hidden_incc_debt"] == pytest.approx(0)


def test_text_report_mentions_the_key_figures(ra):
    text = report(simulate(ra))
    assert "R$ 391.802,30" in text and "SAC:" in text and "PRICE:" in text


def test_payload_exposes_derived_balloons(ra):
    dp = simulation_to_dict(simulate(ra))["down_payment"]
    assert dp["balloons"] == [{"month": 6, "nominal": 13_750.0}, {"month": 12, "nominal": 13_750.0}]
    assert dp["missing_amount"] == 27_500.0
