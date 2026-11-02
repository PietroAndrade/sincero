"""Construction interest (juros de obra / evolução de obra)."""
from __future__ import annotations

from dataclasses import dataclass

from .input_interface import SimulationInputInterface
from .mortgage import MortgageBalance
from .rates import MonthlyRate


@dataclass(frozen=True)
class ConstructionCharge:
    month: int
    released_share: float    # 0..1 share of the financed balance released by the bank so far
    released_balance: float  # corrected balance × released share
    interest: float


class LinearRelease:
    """
    The bank releases the financed balance evenly over the months remaining until
    delivery: after k of N months, k/N has been released.

    This is the only information the input carries (months remaining). Modelling the
    building's physical progress — e.g. a building already 80% built when the buyer signs
    — is a candidate future feature; see docs/future-features/physical-progress.md.
    """

    def __init__(self, months_remaining: int):
        self.months = months_remaining

    def at(self, month: int) -> float:
        return month / self.months


class ConstructionInterest:
    """
    Each month the buyer pays the bank rate on the part of the INCC-corrected balance the
    bank has already released to the developer. Nothing here amortizes the balance.
    """

    def __init__(self, inp: SimulationInputInterface, mortgage: MortgageBalance, bank: MonthlyRate):
        months = inp.contract().months_remaining
        release = LinearRelease(months)
        self.schedule: list[ConstructionCharge] = []
        for k in range(1, months + 1):
            share = release.at(k)
            released = mortgage.at_month(k) * share
            self.schedule.append(ConstructionCharge(k, share, released, released * bank.monthly))

    @property
    def total(self) -> float:
        return sum(c.interest for c in self.schedule)
