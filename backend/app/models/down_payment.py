"""Down payment (entrada) owed to the developer during construction."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import SimulationError
from .input_dto import ContractData
from .input_interface import SimulationInputInterface
from .rates import MonthlyRate

_CENT = 0.005


@dataclass(frozen=True)
class Balloon:
    """A lump sum owed to the developer in a construction month (nominal = before INCC)."""

    month: int
    nominal: float


@dataclass(frozen=True)
class DeveloperPayment:
    month: int
    incc_factor: float
    installment: float   # regular installment, INCC-corrected
    balloon: float       # balloon paid this month, INCC-corrected (0 if none)

    @property
    def total(self) -> float:
        return self.installment + self.balloon


class DownPaymentPlan:
    """
    How the remaining down payment (after upfront credits) reaches the developer.

    * Without a chosen installment, the balance is split in N equal nominal installments.
    * With a chosen installment, the balance the installments do not cover ("missing
      amount") is split equally among the balloon months. The balloon is therefore a
      derived figure: `(remaining − installment × N) / len(balloon_months)`.

    Every payment in month k is corrected by the INCC factor `(1 + incc_pm)^k`.
    """

    def __init__(self, inp: SimulationInputInterface, incc: MonthlyRate):
        self.required = inp.required_down_payment()
        self.upfront = inp.upfront()
        self.remaining = inp.remaining_down_payment()
        n = inp.contract().months_remaining

        self.nominal_installment, self.balloons = self._size_payments(inp.contract(), n)
        balloon_by_month = {b.month: b.nominal for b in self.balloons}
        self.schedule: list[DeveloperPayment] = [
            DeveloperPayment(
                month=k,
                incc_factor=incc.factor(k),
                installment=self.nominal_installment * incc.factor(k),
                balloon=balloon_by_month.get(k, 0.0) * incc.factor(k),
            )
            for k in range(1, n + 1)
        ]

    def _size_payments(self, contract: ContractData, n: int) -> tuple[float, list[Balloon]]:
        if contract.developer_installment is None:
            if contract.balloon_months:
                raise SimulationError("a monthly developer installment is required to size the balloon payments")
            return self.remaining / n, []

        installment = contract.developer_installment
        covered = installment * n
        missing = self.remaining - covered
        rounding = _CENT * n  # an installment rounded to the cent still "covers" the balance
        if missing < -rounding:
            raise SimulationError(
                f"monthly installments of R$ {covered:,.2f} exceed the down payment balance of R$ {self.remaining:,.2f}")
        if missing <= rounding:
            return installment, []
        if not contract.balloon_months:
            raise SimulationError(
                f"monthly installments of R$ {covered:,.2f} do not cover the down payment balance of "
                f"R$ {self.remaining:,.2f}; R$ {missing:,.2f} is missing — add balloon months or raise the installment")
        per_balloon = missing / len(contract.balloon_months)
        return installment, [Balloon(month, per_balloon) for month in sorted(contract.balloon_months)]

    @property
    def missing_amount(self) -> float:
        """What the monthly installments leave for the balloons (nominal)."""
        return sum(b.nominal for b in self.balloons)

    @property
    def nominal_balloon(self) -> float:
        return self.balloons[0].nominal if self.balloons else 0.0

    @property
    def total_paid(self) -> float:
        return sum(p.total for p in self.schedule)

    @property
    def incc_correction(self) -> float:
        return self.total_paid - self.remaining
