"""Month-by-month cash flow from signing (month 0) to the last bank installment."""
from __future__ import annotations

from dataclasses import dataclass

from .amortization import AmortizationSchedule
from .construction import ConstructionInterest
from .down_payment import DownPaymentPlan


@dataclass(frozen=True)
class TimelineMonth:
    month: int
    developer_installment: float = 0.0
    balloon: float = 0.0
    construction_interest: float = 0.0
    bank_installment: float = 0.0
    upfront: float = 0.0

    @property
    def total(self) -> float:
        return (self.developer_installment + self.balloon + self.construction_interest
                + self.bank_installment + self.upfront)


class CashFlowTimeline:
    def __init__(self, dp: DownPaymentPlan, construction: ConstructionInterest, bank: AmortizationSchedule):
        n = len(dp.schedule)
        self.months: list[TimelineMonth] = [TimelineMonth(0, upfront=dp.upfront)]
        for d, c in zip(dp.schedule, construction.schedule):
            self.months.append(TimelineMonth(d.month, developer_installment=d.installment, balloon=d.balloon,
                                             construction_interest=c.interest))
        for i in bank.schedule:
            self.months.append(TimelineMonth(n + i.month, bank_installment=i.installment))
        self.construction_phase = self.months[: n + 1]
        self.peak = max(self.construction_phase, key=lambda m: m.total)

    @property
    def construction_phase_total(self) -> float:
        return sum(m.total for m in self.construction_phase)
