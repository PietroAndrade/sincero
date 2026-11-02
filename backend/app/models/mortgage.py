"""The balance transferred to the bank at delivery, corrected by INCC during construction."""
from __future__ import annotations

from .input_dto import ContractData
from .rates import MonthlyRate


class MortgageBalance:
    def __init__(self, contract: ContractData, incc: MonthlyRate):
        self._incc = incc
        self.months = contract.months_remaining
        # Upfront above the required down payment reduces what is financed.
        self.nominal = contract.list_price - max(contract.required_down_payment, contract.upfront)

    def at_month(self, month: int) -> float:
        """INCC-corrected balance after `month` months of construction."""
        return self.nominal * self._incc.factor(month)

    @property
    def corrected(self) -> float:
        return self.at_month(self.months)

    @property
    def hidden_incc_debt(self) -> float:
        return self.corrected - self.nominal
