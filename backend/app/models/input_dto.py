"""
Data transfer objects: the three groups of values a simulation needs.

Each DTO is a frozen dataclass with one responsibility. Their fields — names, types,
defaults, which may be null, and which group owns them — are declared once, in
`proto/sincero/simulation_input.proto`, and generated into `input_fields.py` (`make dto`;
`make test` fails while the two disagree). The classes here subclass the generated ones and
add the only behaviour a DTO has: the amounts derived from its own fields
(`ContractData.required_down_payment` and friends). Validation rules live in
`validators.py`, orchestration in `simulator.py`.

The defaults are the application's — the single source of truth the CLI reads for `--help`
and the API for `GET /api/fields`.

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

from dataclasses import MISSING, dataclass, fields

from .input_fields import BankCreditFields, ContractFields, MarketFields


@dataclass(frozen=True)
class ContractData(ContractFields):
    """The contract with the developer, plus the amounts that follow from it alone."""

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
class MarketData(MarketFields):
    """Market and regulatory conditions, independent of the property."""


@dataclass(frozen=True)
class BankCreditData(BankCreditFields):
    """The bank's position at signing and the fallback when it falls short at delivery."""


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
