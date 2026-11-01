"""Everything paid on top of the list price until delivery (the 'R$ 274k -> R$ 369k' view)."""
from __future__ import annotations

from dataclasses import dataclass

from .closing_costs import ClosingCosts
from .construction import ConstructionInterest
from .down_payment import DownPaymentPlan
from .inputs import SimulationInput
from .mortgage import MortgageBalance


@dataclass(frozen=True)
class CostLine:
    component: str
    base_value: float
    additional: float

    @property
    def final_value(self) -> float:
        return self.base_value + self.additional


class TotalCost:
    def __init__(self, inp: SimulationInput, dp: DownPaymentPlan, mortgage: MortgageBalance,
                 construction: ConstructionInterest, closing: ClosingCosts):
        self.list_price = inp.list_price
        self.lines = [
            # the base column adds up to the list price even when upfront > down payment
            CostLine("Down payment", max(dp.required, dp.upfront), dp.incc_correction),
            CostLine("Mortgage balance", mortgage.nominal, mortgage.hidden_incc_debt),
            CostLine("Construction interest", 0.0, construction.total),
            CostLine("Closing costs", 0.0, closing.total),
        ]

    @property
    def additional(self) -> float:
        return sum(line.additional for line in self.lines)

    @property
    def total(self) -> float:
        return self.list_price + self.additional

    @property
    def extra_pct(self) -> float:
        return self.additional / self.list_price * 100.0

    @property
    def total_line(self) -> CostLine:
        return CostLine("Total", self.list_price, self.additional)
