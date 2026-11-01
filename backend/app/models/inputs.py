"""Input model of a simulation and its validation rules."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from .errors import SimulationError


@dataclass(frozen=True)
class SimulationInput:
    # Property / contract
    name: str
    list_price: float
    months_remaining: int          # months left until the building is delivered (not its total duration)
    down_payment_pct: float = 20.0
    fgts_upfront: float = 0.0
    cash_upfront: float = 0.0
    # How the remaining down payment is paid to the developer. When `developer_installment`
    # is None the balance is simply split in equal installments. When the buyer chooses an
    # installment, whatever it does not cover is paid as balloons in `balloon_months`
    # (the balloon amount is derived, never typed in).
    developer_installment: Optional[float] = None
    balloon_months: tuple[int, ...] = field(default_factory=tuple)
    # Market
    incc_rate_pa: float = 7.0
    bank_rate_pa: float = 10.26
    term_months: int = 360
    itbi_pct: float = 2.0
    registry_pct: float = 0.5
    income_commitment_ratio: float = 0.30
    # Bank credit
    pre_approved_credit: Optional[float] = None
    pro_soluto_months: int = 12

    def __post_init__(self):
        object.__setattr__(self, "balloon_months", tuple(self.balloon_months))

    # ----- derived amounts shared by several components -------------------
    @property
    def required_down_payment(self) -> float:
        return self.list_price * self.down_payment_pct / 100.0

    @property
    def upfront(self) -> float:
        return self.fgts_upfront + self.cash_upfront

    @property
    def remaining_down_payment(self) -> float:
        return max(0.0, self.required_down_payment - self.upfront)

    # ----- validation -----------------------------------------------------
    def validate(self) -> "SimulationInput":
        if self.list_price <= 0:
            raise SimulationError("list price must be greater than zero")
        if self.months_remaining < 1:
            raise SimulationError("months remaining until delivery must be at least 1")
        if self.term_months < 1:
            raise SimulationError("financing term must be at least 1 month")
        if not 0 < self.income_commitment_ratio <= 1:
            raise SimulationError("income commitment ratio must be between 0 and 1")
        if self.fgts_upfront < 0 or self.cash_upfront < 0:
            raise SimulationError("upfront payments must not be negative")
        if self.developer_installment is not None and self.developer_installment < 0:
            raise SimulationError("the monthly developer installment must not be negative")
        for month in self.balloon_months:
            if month > self.months_remaining:
                raise SimulationError(f"balloon month {month} is after delivery (month {self.months_remaining})")
            if month < 1:
                raise SimulationError(f"balloon month {month} must be at least 1")
        if len(set(self.balloon_months)) != len(self.balloon_months):
            raise SimulationError("balloon months must not repeat")
        return self

    def with_overrides(self, **overrides) -> "SimulationInput":
        """A copy with some fields changed — the basis of every what-if."""
        return replace(self, **overrides)
