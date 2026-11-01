"""Bank amortization systems used in Brazil: SAC and PRICE (Tabela Price)."""
from __future__ import annotations

from dataclasses import dataclass

from .rates import MonthlyRate


@dataclass(frozen=True)
class Installment:
    month: int
    installment: float
    interest: float
    amortization: float
    outstanding: float  # balance after this payment


class AmortizationSchedule:
    """Base class: builds a schedule and derives the summary figures from it."""

    name: str = ""

    def __init__(self, principal: float, rate: MonthlyRate, term_months: int, income_ratio: float):
        self.principal = principal
        self.rate = rate
        self.term_months = term_months
        self.income_ratio = income_ratio
        self.schedule: list[Installment] = self._build()

    def _build(self) -> list[Installment]:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def first_installment(self) -> float:
        return self.schedule[0].installment

    @property
    def last_installment(self) -> float:
        return self.schedule[-1].installment

    @property
    def total_interest(self) -> float:
        return sum(i.interest for i in self.schedule)

    @property
    def total_paid(self) -> float:
        return sum(i.installment for i in self.schedule)

    @property
    def min_income(self) -> float:
        return self.first_installment / self.income_ratio


class SacSchedule(AmortizationSchedule):
    """Sistema de Amortização Constante: fixed amortization, decreasing installments."""

    name = "SAC"

    @property
    def amortization(self) -> float:
        return self.principal / self.term_months

    def _build(self) -> list[Installment]:
        amort, i = self.principal / self.term_months, self.rate.monthly
        rows, outstanding = [], self.principal
        for k in range(1, self.term_months + 1):
            interest = outstanding * i
            outstanding -= amort
            rows.append(Installment(k, amort + interest, interest, amort, outstanding))
        return rows


class PriceSchedule(AmortizationSchedule):
    """Tabela Price: fixed installment, increasing amortization."""

    name = "PRICE"

    @property
    def installment(self) -> float:
        i = self.rate.monthly
        if i == 0:
            return self.principal / self.term_months
        return self.principal * i / (1 - (1 + i) ** (-self.term_months))

    def _build(self) -> list[Installment]:
        pmt, i = self.installment, self.rate.monthly
        rows, outstanding = [], self.principal
        for k in range(1, self.term_months + 1):
            interest = outstanding * i
            amort = pmt - interest
            outstanding -= amort
            rows.append(Installment(k, pmt, interest, amort, outstanding))
        return rows
