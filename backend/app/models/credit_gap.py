"""The 'Caixa trigger': extra credit needed at delivery and the resulting pro-soluto."""
from __future__ import annotations

from .inputs import SimulationInput
from .mortgage import MortgageBalance


class CreditGap:
    def __init__(self, inp: SimulationInput, mortgage: MortgageBalance):
        self.pre_approved = inp.pre_approved_credit if inp.pre_approved_credit is not None else mortgage.nominal
        self.needed = mortgage.corrected
        self.gap = max(0.0, self.needed - self.pre_approved)
        self.pro_soluto_months = inp.pro_soluto_months
        self.pro_soluto_installment = self.gap / inp.pro_soluto_months if inp.pro_soluto_months > 0 else 0.0
