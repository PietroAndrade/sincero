"""Orchestrates every component of the model into one SimulationResult."""
from __future__ import annotations

from dataclasses import dataclass

from .amortization import PriceSchedule, SacSchedule
from .closing_costs import ClosingCosts
from .construction import ConstructionInterest
from .credit_gap import CreditGap
from .down_payment import DownPaymentPlan
from .input_interface import SimulationInputInterface
from .mortgage import MortgageBalance
from .rates import MonthlyRate
from .timeline import CashFlowTimeline
from .total_cost import TotalCost


@dataclass
class SimulationResult:
    input: SimulationInputInterface
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

    def __init__(self, inp: SimulationInputInterface):
        self.input = inp.validate()

    def run(self) -> SimulationResult:
        inp, market = self.input, self.input.market()
        incc, bank = MonthlyRate(market.incc_rate_pa), MonthlyRate(market.bank_rate_pa)

        down_payment = DownPaymentPlan(inp, incc)
        mortgage = MortgageBalance(inp, incc)
        construction = ConstructionInterest(inp, mortgage, bank)
        closing = ClosingCosts(inp)
        sac = SacSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio)
        price = PriceSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio)
        credit_gap = CreditGap(inp, mortgage)
        total_cost = TotalCost(inp, down_payment, mortgage, construction, closing)
        timeline = CashFlowTimeline(down_payment, construction, sac)

        return SimulationResult(inp, incc, bank, down_payment, mortgage, construction, closing,
                                sac, price, credit_gap, total_cost, timeline)


def simulate(inp: SimulationInputInterface) -> SimulationResult:
    return OffPlanSimulator(inp).run()
