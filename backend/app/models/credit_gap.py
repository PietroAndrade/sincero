"""The 'Caixa trigger': extra credit needed at delivery and the resulting pro-soluto."""
from __future__ import annotations

from .input_interface import SimulationInputInterface
from .mortgage import MortgageBalance


class CreditGap:
    def __init__(self, inp: SimulationInputInterface, mortgage: MortgageBalance):
        credit = inp.bank_credit()
        self.pre_approved = credit.pre_approved_credit if credit.pre_approved_credit is not None else mortgage.nominal
        self.needed = mortgage.corrected
        self.gap = max(0.0, self.needed - self.pre_approved)
        self.pro_soluto_months = credit.pro_soluto_months
        self.pro_soluto_installment = self.gap / credit.pro_soluto_months if credit.pro_soluto_months > 0 else 0.0
