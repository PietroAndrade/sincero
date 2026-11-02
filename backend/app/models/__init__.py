"""Domain model. Pure Python: no Flask, no JSON, no printing."""
from .comparison import Variation, WhatIf, cash_ladder, compare, what_if
from .errors import SimulationError
from .down_payment import Balloon
from .input_dto import BankCreditData, ContractData, MarketData, field_defaults, field_names
from .input_interface import SimulationInputInterface
from .inputs import SimulationInput
from .rates import MonthlyRate, annual_to_monthly
from .simulator import OffPlanSimulator, SimulationResult, simulate
from .validators import DEFAULT_POLICY, CompositeValidator, ValidationPolicy, Validator

__all__ = [
    "Balloon", "SimulationInput", "SimulationInputInterface", "ContractData", "MarketData", "BankCreditData",
    "field_names", "field_defaults", "SimulationError", "SimulationResult",
    "OffPlanSimulator", "Validator", "CompositeValidator", "ValidationPolicy", "DEFAULT_POLICY",
    "MonthlyRate", "annual_to_monthly", "simulate", "compare", "what_if", "cash_ladder",
    "WhatIf", "Variation",
]
