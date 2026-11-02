"""Plain-text report for the terminal."""
from __future__ import annotations

from app.models import SimulationResult


def brl(value: float) -> str:
    """R$ 1.234,56"""
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def report(r: SimulationResult) -> str:
    inp, dp, ci, cg, tl = r.input.contract, r.down_payment, r.construction_interest, r.credit_gap, r.timeline
    lines = [
        "=" * 72,
        f"🏠 {inp.name}  |  {brl(inp.list_price)}  |  {inp.months_remaining} months remaining",
        "=" * 72,
        f"{'Component':<24}{'Base':>15}{'Additional':>16}{'Final':>17}",
    ]
    for line in [*r.total_cost.lines, r.total_cost.total_line]:
        lines.append(f"{line.component:<24}{brl(line.base_value):>15}{brl(line.additional):>16}{brl(line.final_value):>17}")
    lines += [
        f"Extra cost over list price: {r.total_cost.extra_pct:.2f}%",
        "",
        f"Developer: {brl(dp.nominal_installment)}/month nominal  "
        f"(month 1: {brl(dp.schedule[0].installment)}, last: {brl(dp.schedule[-1].installment)})"
        + (f"  +  {len(dp.balloons)} balloon(s) of {brl(dp.nominal_balloon)} nominal in months "
           f"{', '.join(str(b.month) for b in dp.balloons)}" if dp.balloons else ""),
        f"Construction interest: month 1 {brl(ci.schedule[0].interest)} → last {brl(ci.schedule[-1].interest)}"
        f"  |  total {brl(ci.total)}",
        f"SAC:   1st {brl(r.sac.first_installment)}  last {brl(r.sac.last_installment)}  min income {brl(r.sac.min_income)}",
        f"PRICE: fixed {brl(r.price.installment)}  min income {brl(r.price.min_income)}",
        f"Credit gap at delivery: {brl(cg.gap)} (pre-approved {brl(cg.pre_approved)} vs needed {brl(cg.needed)})"
        f" → pro-soluto {brl(cg.pro_soluto_installment)} x {cg.pro_soluto_months}",
        f"Peak month: {tl.peak.month} ({brl(tl.peak.total)})  |  construction phase total {brl(tl.construction_phase_total)}",
    ]
    return "\n".join(lines)


def comparison_table(results: list[SimulationResult]) -> str:
    header = (f"{'Name':<5}{'Price':>14}{'Left':>5}{'Dev/mo':>13}{'Hidden INCC':>14}{'Balance@deliv':>16}"
              f"{'Constr.int':>13}{'SAC 1st':>12}{'Min income':>14}")
    rows = [
        f"{c.name:<5}{brl(c.list_price):>14}{c.months_remaining:>5}"
        f"{brl(r.down_payment.nominal_installment):>13}{brl(r.mortgage.hidden_incc_debt):>14}"
        f"{brl(r.mortgage.corrected):>16}{brl(r.construction_interest.total):>13}"
        f"{brl(r.sac.first_installment):>12}{brl(r.sac.min_income):>14}"
        for r in results
        for c in [r.input.contract]
    ]
    return "\n".join([header, *rows])
