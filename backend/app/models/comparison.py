"""Side-by-side runs: several properties, or one property under alternative assumptions."""
from __future__ import annotations

from dataclasses import dataclass

from .input_interface import SimulationInputInterface
from .simulator import SimulationResult, simulate


def compare(inputs: list[SimulationInputInterface]) -> list[SimulationResult]:
    return [simulate(inp) for inp in inputs]


@dataclass(frozen=True)
class Variation:
    label: str
    overrides: dict
    result: SimulationResult


@dataclass(frozen=True)
class WhatIf:
    base: SimulationResult
    variations: list[Variation]


def what_if(base: SimulationInputInterface, variations: dict[str, dict]) -> WhatIf:
    """
    Run `base` and each named variation (a dict of input field overrides, any DTO).

    >>> what_if(inp, {"INCC 4%": {"incc_rate_pa": 4.0}, "R$ 30k cash": {"cash_upfront": 30_000}})
    """
    return WhatIf(
        base=simulate(base),
        variations=[Variation(label, overrides, simulate(base.with_overrides(**overrides)))
                    for label, overrides in variations.items()],
    )


def cash_ladder(base: SimulationInputInterface, amounts: list[float]) -> WhatIf:
    """The 'more cash' simulation: the same contract with increasing cash at signing."""
    return what_if(base, {f"cash {amount:,.2f}": {"cash_upfront": amount} for amount in amounts})
