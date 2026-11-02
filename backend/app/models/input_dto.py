"""
Data transfer objects: the three groups of values a simulation needs.

Each DTO is a frozen dataclass with one responsibility. They carry the application's
defaults — the single source of truth the CLI reads for `--help`. The only behaviour a
DTO has is the amounts derived from its own fields (`ContractData.required_down_payment`
and friends); validation rules live in `validators.py`, orchestration in `simulator.py`.

Components receive the DTO they need, never the whole simulation input:
`DownPaymentPlan(contract, …)`, `ClosingCosts(list_price, market)`, `CreditGap(bank_credit, …)`.

    ContractData    what the buyer signs with the developer
    MarketData      the economic environment: rates, financing term, fees, income ceiling
    BankCreditData  what the bank pre-approved and how a credit gap is paid

The field names are unique across the three groups so a flat mapping of `field -> value`
(a JSON body, argparse flags, a what-if override) can be routed to the right DTO with
`FIELD_OWNER`.
"""
from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from typing import Optional


@dataclass(frozen=True)
class ContractData:
    """The contract with the developer: the property, the down payment and how it is paid."""

    name: str
    list_price: float
    months_remaining: int          # months left until the building is delivered (not its total duration)
    down_payment_pct: float = 20.0
    fgts_upfront: float = 0.0
    cash_upfront: float = 0.0
    # When `developer_installment` is None the remaining down payment is split in equal
    # installments. When the buyer chooses an installment, whatever it does not cover is
    # paid as balloons in `balloon_months` (the balloon amount is derived, never typed in).
    developer_installment: Optional[float] = None
    balloon_months: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(self, "balloon_months", tuple(self.balloon_months))

    # ----- amounts derived from the contract alone ------------------------
    @property
    def required_down_payment(self) -> float:
        """Down payment demanded by the developer: `list_price × down_payment_pct`."""
        return self.list_price * self.down_payment_pct / 100.0

    @property
    def upfront(self) -> float:
        """Everything paid at signing (FGTS + cash)."""
        return self.fgts_upfront + self.cash_upfront

    @property
    def remaining_down_payment(self) -> float:
        """Down payment still owed to the developer after the upfront credits (never negative)."""
        return max(0.0, self.required_down_payment - self.upfront)


@dataclass(frozen=True)
class MarketData:
    """Market and regulatory conditions, independent of the property."""

    incc_rate_pa: float = 7.0
    bank_rate_pa: float = 10.26
    term_months: int = 360
    itbi_pct: float = 2.0
    registry_pct: float = 0.5
    income_commitment_ratio: float = 0.30


@dataclass(frozen=True)
class BankCreditData:
    """The bank's position at signing and the fallback when it falls short at delivery."""

    pre_approved_credit: Optional[float] = None   # None: the nominal mortgage balance
    pro_soluto_months: int = 12


INPUT_GROUPS: tuple[type, ...] = (ContractData, MarketData, BankCreditData)

# field name -> the DTO that owns it
FIELD_OWNER: dict[str, type] = {f.name: dto for dto in INPUT_GROUPS for f in fields(dto)}
assert len(FIELD_OWNER) == sum(len(fields(dto)) for dto in INPUT_GROUPS), "input field names must be unique"


def field_names() -> tuple[str, ...]:
    """Every input field, in DTO order."""
    return tuple(FIELD_OWNER)


def field_defaults() -> dict:
    """Default of every input field that has one."""
    return {f.name: f.default for dto in INPUT_GROUPS for f in fields(dto) if f.default is not MISSING}
