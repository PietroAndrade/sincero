"""
JSON presenters. The dict returned by `simulation_to_dict` is the payload contract of
the API and the front-end; the behave suite asserts against it.
"""
from __future__ import annotations

from dataclasses import asdict

from app.models import SimulationInput, SimulationResult, WhatIf
from app.models.amortization import AmortizationSchedule, PriceSchedule, SacSchedule


def input_to_dict(inp: SimulationInput) -> dict:
    data = asdict(inp)
    data["balloon_months"] = list(inp.balloon_months)
    return data


def input_from_dict(data: dict) -> SimulationInput:
    """Inverse of input_to_dict — used by controllers to read a request body."""
    data = dict(data)
    data["balloon_months"] = tuple(int(m) for m in data.get("balloon_months", ()))
    return SimulationInput(**data)


def _schedule_to_dict(schedule: AmortizationSchedule) -> dict:
    data = {
        "first_installment": schedule.first_installment,
        "last_installment": schedule.last_installment,
        "total_interest": schedule.total_interest,
        "total_paid": schedule.total_paid,
        "min_income": schedule.min_income,
        "schedule": [asdict(i) for i in schedule.schedule],
    }
    if isinstance(schedule, SacSchedule):
        data["amortization"] = schedule.amortization
    if isinstance(schedule, PriceSchedule):
        data["installment"] = schedule.installment
    return data


def simulation_to_dict(r: SimulationResult) -> dict:
    dp, mortgage, ci, closing, cg, tc, tl = (r.down_payment, r.mortgage, r.construction_interest,
                                             r.closing_costs, r.credit_gap, r.total_cost, r.timeline)
    return {
        "input": input_to_dict(r.input),
        "rates": {"incc_pm": r.incc.monthly, "bank_pm": r.bank.monthly},
        "down_payment": {
            "required": dp.required,
            "upfront": dp.upfront,
            "remaining": dp.remaining,
            "nominal_installment": dp.nominal_installment,
            "missing_amount": dp.missing_amount,
            "nominal_balloon": dp.nominal_balloon,
            "balloons": [asdict(b) for b in dp.balloons],
            "total_paid": dp.total_paid,
            "incc_correction": dp.incc_correction,
            "schedule": [asdict(p) for p in dp.schedule],
        },
        "mortgage": {
            "nominal_balance": mortgage.nominal,
            "corrected_balance": mortgage.corrected,
            "hidden_incc_debt": mortgage.hidden_incc_debt,
        },
        "construction_interest": {"total": ci.total, "schedule": [asdict(c) for c in ci.schedule]},
        "closing_costs": {"itbi": closing.itbi, "registry": closing.registry, "total": closing.total},
        "financing": {"sac": _schedule_to_dict(r.sac), "price": _schedule_to_dict(r.price)},
        "credit_gap": {
            "pre_approved": cg.pre_approved,
            "needed": cg.needed,
            "gap": cg.gap,
            "pro_soluto_months": cg.pro_soluto_months,
            "pro_soluto_installment": cg.pro_soluto_installment,
        },
        "total_cost": {
            "list_price": tc.list_price,
            "additional": tc.additional,
            "total": tc.total,
            "extra_pct": tc.extra_pct,
            "breakdown": [
                {"component": line.component, "base_value": line.base_value,
                 "additional": line.additional, "final_value": line.final_value}
                for line in [*tc.lines, tc.total_line]
            ],
        },
        "timeline": {
            "months": [{**asdict(m), "total": m.total} for m in tl.months],
            "peak_month": tl.peak.month,
            "peak_total": tl.peak.total,
            "construction_phase_total": tl.construction_phase_total,
        },
    }


def summary_to_dict(r: SimulationResult) -> dict:
    """Flat, table/chart friendly figures — one row of a comparison."""
    return {
        "name": r.input.name,
        "list_price": r.input.list_price,
        "months_remaining": r.input.months_remaining,
        "cash_upfront": r.input.cash_upfront,
        "developer_installment": r.down_payment.nominal_installment,
        "nominal_balloon": r.down_payment.nominal_balloon,
        "incc_on_down_payment": r.down_payment.incc_correction,
        "hidden_incc_debt": r.mortgage.hidden_incc_debt,
        "balance_at_delivery": r.mortgage.corrected,
        "construction_interest": r.construction_interest.total,
        "closing_costs": r.closing_costs.total,
        "sac_first_installment": r.sac.first_installment,
        "sac_last_installment": r.sac.last_installment,
        "price_installment": r.price.installment,
        "min_income_sac": r.sac.min_income,
        "min_income_price": r.price.min_income,
        "credit_gap": r.credit_gap.gap,
        "total_cost": r.total_cost.total,
        "extra_pct": r.total_cost.extra_pct,
        "peak_month": r.timeline.peak.month,
        "peak_total": r.timeline.peak.total,
    }


def comparison_to_dict(results: list[SimulationResult]) -> list[dict]:
    return [summary_to_dict(r) for r in results]


def what_if_to_dict(w: WhatIf) -> dict:
    base = summary_to_dict(w.base)
    scenarios = []
    for v in w.variations:
        summary = summary_to_dict(v.result)
        delta = {k: summary[k] - base[k] for k, value in summary.items() if isinstance(value, (int, float))}
        scenarios.append({"label": v.label, "overrides": v.overrides, "summary": summary, "delta": delta})
    return {"base": base, "scenarios": scenarios}


def error_to_dict(exc: Exception) -> dict:
    return {"error": str(exc)}
