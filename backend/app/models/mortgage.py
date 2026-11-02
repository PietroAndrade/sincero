"""The balance transferred to the bank at delivery, corrected by INCC during construction."""
from __future__ import annotations

from .input_interface import SimulationInputInterface
from .rates import MonthlyRate


class MortgageBalance:
    def __init__(self, inp: SimulationInputInterface, incc: MonthlyRate):
        self._incc = incc
        self.months = inp.contract().months_remaining
        # Upfront above the required down payment reduces what is financed.
        self.nominal = inp.contract().list_price - max(inp.required_down_payment(), inp.upfront())

    def at_month(self, month: int) -> float:
        """INCC-corrected balance after `month` months of construction."""
        return self.nominal * self._incc.factor(month)

    @property
    def corrected(self) -> float:
        return self.at_month(self.months)

    @property
    def hidden_incc_debt(self) -> float:
        return self.corrected - self.nominal
