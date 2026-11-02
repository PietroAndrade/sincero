"""
Input validation rules, one small validator per concern.

Validators read the inputs through the interface's DTO accessors (`contract()`,
`market()`, `bank_credit()`); each one touches a single DTO. Every validator implements `InputValidator.validate(inp)` and raises `SimulationError`
with a user-facing message on the first rule it finds broken. `CompositeValidator`
chains them in a fixed order, so the error a buyer sees is always the most fundamental
one (property data before market data, market data before bank credit…).

`default_validator()` is what `SimulationInput.validate()` uses. Components that need a
different policy (an API endpoint, a test) can build their own composite or pass a
single validator instead.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from .errors import SimulationError
from .input_interface import SimulationInputInterface


class InputValidator(ABC):
    """One validation concern. Raises `SimulationError` on the first broken rule."""

    @abstractmethod
    def validate(self, inp: SimulationInputInterface) -> None:
        ...


# ----- property / contract ---------------------------------------------------
class PropertyValidator(InputValidator):
    """The property itself: price, time left until delivery, required down payment."""

    def validate(self, inp: SimulationInputInterface) -> None:
        c = inp.contract()
        if c.list_price <= 0:
            raise SimulationError("list price must be greater than zero")
        if c.months_remaining < 1:
            raise SimulationError("months remaining until delivery must be at least 1")
        if not 0 <= c.down_payment_pct <= 100:
            raise SimulationError("down payment percentage must be between 0 and 100")


class UpfrontPaymentsValidator(InputValidator):
    """
    What the buyer brings at signing. FGTS and cash may together cover the whole price
    (a cash purchase: nothing left to finance) but never more — there is nothing to pay
    the excess for, and the model would otherwise finance a negative balance.
    """

    def validate(self, inp: SimulationInputInterface) -> None:
        c = inp.contract()
        if c.fgts_upfront < 0 or c.cash_upfront < 0:
            raise SimulationError("upfront payments must not be negative")
        if inp.upfront() > c.list_price:
            raise SimulationError(
                f"upfront payments of R$ {inp.upfront():,.2f} exceed the list price of R$ {c.list_price:,.2f}")


class DeveloperPlanValidator(InputValidator):
    """
    The payment plan agreed with the developer: monthly installment and balloon months.
    Whether the installments and balloons actually cover the balance is a sizing
    question answered by `DownPaymentPlan`, not a shape question answered here.
    """

    def validate(self, inp: SimulationInputInterface) -> None:
        c = inp.contract()
        if c.developer_installment is not None and c.developer_installment < 0:
            raise SimulationError("the monthly developer installment must not be negative")
        for month in c.balloon_months:
            if month > c.months_remaining:
                raise SimulationError(f"balloon month {month} is after delivery (month {c.months_remaining})")
            if month < 1:
                raise SimulationError(f"balloon month {month} must be at least 1")
        if len(set(c.balloon_months)) != len(c.balloon_months):
            raise SimulationError("balloon months must not repeat")


# ----- market ----------------------------------------------------------------
class MarketRatesValidator(InputValidator):
    """
    Annual rates that are compounded monthly. INCC may be negative (deflation) but an
    annual rate of −100% or below has no monthly equivalent; a bank never lends at a
    negative rate.
    """

    def validate(self, inp: SimulationInputInterface) -> None:
        m = inp.market()
        if m.incc_rate_pa <= -100:
            raise SimulationError("INCC rate must be greater than -100% per year")
        if m.bank_rate_pa < 0:
            raise SimulationError("bank interest rate must not be negative")


class FinancingValidator(InputValidator):
    """Terms of the bank financing after key handover."""

    def validate(self, inp: SimulationInputInterface) -> None:
        m = inp.market()
        if m.term_months < 1:
            raise SimulationError("financing term must be at least 1 month")
        if not 0 < m.income_commitment_ratio <= 1:
            raise SimulationError("income commitment ratio must be between 0 and 1")


class ClosingCostsValidator(InputValidator):
    """ITBI and registry/deed, as percentages of the list price."""

    def validate(self, inp: SimulationInputInterface) -> None:
        m = inp.market()
        if m.itbi_pct < 0 or m.registry_pct < 0:
            raise SimulationError("closing cost percentages must not be negative")


# ----- bank credit -----------------------------------------------------------
class BankCreditValidator(InputValidator):
    """Pre-approved credit and the pro-soluto term used to pay any credit gap."""

    def validate(self, inp: SimulationInputInterface) -> None:
        b = inp.bank_credit()
        if b.pre_approved_credit is not None and b.pre_approved_credit < 0:
            raise SimulationError("pre-approved credit must not be negative")
        if b.pro_soluto_months < 1:
            raise SimulationError("pro-soluto term must be at least 1 month")


# ----- composition -----------------------------------------------------------
class CompositeValidator(InputValidator):
    """Runs validators in order; the first `SimulationError` raised wins."""

    def __init__(self, validators: Iterable[InputValidator]):
        self.validators: tuple[InputValidator, ...] = tuple(validators)

    def validate(self, inp: SimulationInputInterface) -> None:
        for validator in self.validators:
            validator.validate(inp)


DEFAULT_VALIDATORS: tuple[InputValidator, ...] = (
    PropertyValidator(),
    UpfrontPaymentsValidator(),
    DeveloperPlanValidator(),
    MarketRatesValidator(),
    FinancingValidator(),
    ClosingCostsValidator(),
    BankCreditValidator(),
)


def default_validator() -> InputValidator:
    """The validation policy of the application: every rule, in the order above."""
    return CompositeValidator(DEFAULT_VALIDATORS)
