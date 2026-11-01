"""Domain model. Pure Python: no Flask, no JSON, no printing."""
from .comparison import Variation, WhatIf, cash_ladder, compare, what_if
from .errors import SimulationError
from .down_payment import Balloon
from .inputs import SimulationInput
from .rates import MonthlyRate, annual_to_monthly
from .simulator import OffPlanSimulator, SimulationResult, simulate

__all__ = [
    "Balloon", "SimulationInput", "SimulationError", "SimulationResult", "OffPlanSimulator",
    "MonthlyRate", "annual_to_monthly", "simulate", "compare", "what_if", "cash_ladder",
    "WhatIf", "Variation",
]
