"""Structural invariants of the domain model that the business features do not spell out."""
import pytest

from app.models import ContractData, SimulationError, SimulationInput, cash_ladder, simulate, what_if


@pytest.fixture
def ra() -> SimulationInput:
    return SimulationInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500, balloon_months=(6, 12)))


def test_schedules_end_with_zero_balance(ra):
    r = simulate(ra)
    assert abs(r.sac.schedule[-1].outstanding) < 1e-6
    assert abs(r.price.schedule[-1].outstanding) < 1e-6
    assert len(r.sac.schedule) == len(r.price.schedule) == 360


def test_amortizations_add_up_to_the_principal(ra):
    r = simulate(ra)
    assert sum(i.amortization for i in r.sac.schedule) == pytest.approx(r.mortgage.corrected)
    assert sum(i.amortization for i in r.price.schedule) == pytest.approx(r.mortgage.corrected)


def test_price_costs_more_interest_than_sac(ra):
    r = simulate(ra)
    assert r.price.total_interest > r.sac.total_interest
    assert r.price.installment < r.sac.first_installment


def test_timeline_total_matches_components(ra):
    r = simulate(ra)
    expected = (r.down_payment.upfront + r.down_payment.total_paid
                + r.construction_interest.total + r.sac.total_paid)
    assert sum(m.total for m in r.timeline.months) == pytest.approx(expected)


def test_cost_breakdown_base_column_adds_up_to_the_list_price(ra):
    for inp in (ra, ra.with_overrides(cash_upfront=100_000, developer_installment=None, balloon_months=())):
        r = simulate(inp)
        assert sum(line.base_value for line in r.total_cost.lines) == pytest.approx(inp.contract().list_price)


def test_what_if_runs_each_variation(ra):
    ra = ra.with_overrides(developer_installment=None, balloon_months=())
    w = what_if(ra, {"low incc": {"incc_rate_pa": 4.0}, "more cash": {"cash_upfront": 30_000}})
    assert [v.label for v in w.variations] == ["low incc", "more cash"]
    assert w.variations[0].result.mortgage.hidden_incc_debt < w.base.mortgage.hidden_incc_debt
    assert w.variations[1].result.down_payment.nominal_installment < w.base.down_payment.nominal_installment


def test_cash_ladder_is_monotonic(ra):
    base = ra.with_overrides(developer_installment=None, balloon_months=())
    w = cash_ladder(base, [0, 30_000, 75_000, 100_000])
    installments = [v.result.down_payment.nominal_installment for v in w.variations]
    balances = [v.result.mortgage.corrected for v in w.variations]
    assert installments == sorted(installments, reverse=True)
    assert balances == sorted(balances, reverse=True)


def test_inputs_are_immutable(ra):
    with pytest.raises(AttributeError):
        ra.list_price = 1  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ra._contract = None  # type: ignore[misc]
    with pytest.raises(Exception):
        ra.contract().list_price = 1  # type: ignore[misc]


@pytest.mark.parametrize("field,value,message", [
    ("term_months", 0, "financing term must be at least 1 month"),
    ("income_commitment_ratio", 0, "income commitment ratio must be between 0 and 1"),
    ("cash_upfront", -1, "upfront payments must not be negative"),
    ("balloon_months", (0,), "balloon month 0 must be at least 1"),
    ("balloon_months", (6, 6), "balloon months must not repeat"),
    ("developer_installment", -1, "the monthly developer installment must not be negative"),
    # Rules added with the validator refactor: these used to crash or to produce a nonsense result.
    ("down_payment_pct", 150, "down payment percentage must be between 0 and 100"),
    ("incc_rate_pa", -100, "INCC rate must be greater than -100% per year"),
    ("bank_rate_pa", -1, "bank interest rate must not be negative"),
    ("itbi_pct", -3, "closing cost percentages must not be negative"),
    ("pre_approved_credit", -1000, "pre-approved credit must not be negative"),
    ("pro_soluto_months", 0, "pro-soluto term must be at least 1 month"),
    ("cash_upfront", 500_000, r"upfront payments of R\$ 513,000.00 exceed the list price of R\$ 440,000.00"),
])
def test_extra_validation_rules(ra, field, value, message):
    with pytest.raises(SimulationError, match=message):
        simulate(ra.with_overrides(**{field: value}))


def test_balloons_are_derived_from_the_uncovered_amount(ra):
    r = simulate(ra)
    assert [b.month for b in r.down_payment.balloons] == [6, 12]
    assert r.down_payment.missing_amount == pytest.approx(75_000 - 2_500 * 19)
    assert r.down_payment.nominal_balloon == pytest.approx(13_750)
    nominal_total = r.down_payment.nominal_installment * 19 + r.down_payment.missing_amount
    assert nominal_total == pytest.approx(r.down_payment.remaining)


def test_paying_the_whole_price_upfront_is_a_cash_purchase(ra):
    r = simulate(ra.with_overrides(fgts_upfront=0, cash_upfront=440_000, developer_installment=None, balloon_months=()))
    assert r.mortgage.nominal == 0 and r.mortgage.corrected == 0
    assert r.construction_interest.total == 0 and r.sac.first_installment == 0
    assert r.total_cost.additional == pytest.approx(r.closing_costs.total)


def test_installment_rounded_to_the_cent_counts_as_covering_the_balance(ra):
    r = simulate(ra.with_overrides(developer_installment=3_947.37, balloon_months=()))
    assert r.down_payment.balloons == []
