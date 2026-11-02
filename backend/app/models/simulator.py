"""Orchestrates every component of the model into one SimulationResult."""
from __future__ import annotations

from dataclasses import dataclass

from .amortization import PriceSchedule, SacSchedule
from .closing_costs import ClosingCosts
from .construction import ConstructionInterest
from .credit_gap import CreditGap
from .down_payment import DownPaymentPlan
from .inputs import SimulationInput
from .mortgage import MortgageBalance
from .rates import MonthlyRate
from .timeline import CashFlowTimeline
from .total_cost import TotalCost


@dataclass
class SimulationResult:
    input: SimulationInput
    incc: MonthlyRate
    bank: MonthlyRate
    down_payment: DownPaymentPlan
    mortgage: MortgageBalance
    construction_interest: ConstructionInterest
    closing_costs: ClosingCosts
    sac: SacSchedule
    price: PriceSchedule
    credit_gap: CreditGap
    total_cost: TotalCost
    timeline: CashFlowTimeline


class OffPlanSimulator:
    """Runs the full off-plan model for one SimulationInput."""

    def __init__(self, inp: SimulationInput):
        self.input = inp.validate()

    def run(self) -> SimulationResult:
        contract, market, credit = self.input.contract, self.input.market, self.input.bank_credit
        incc, bank = MonthlyRate(market.incc_rate_pa), MonthlyRate(market.bank_rate_pa)

        # Each component receives only the DTO (or value) it needs.
        down_payment = DownPaymentPlan(contract, incc)
        mortgage = MortgageBalance(contract, incc)
        construction = ConstructionInterest(mortgage, bank)
        closing = ClosingCosts(contract.list_price, market)
        sac = SacSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio)
        price = PriceSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio)
        credit_gap = CreditGap(credit, mortgage)
        total_cost = TotalCost(contract.list_price, down_payment, mortgage, construction, closing)
        timeline = CashFlowTimeline(down_payment, construction, sac)

        return SimulationResult(self.input, incc, bank, down_payment, mortgage, construction, closing,
                                sac, price, credit_gap, total_cost, timeline)


def simulate(inp: SimulationInput) -> SimulationResult:
    return OffPlanSimulator(inp).run()
