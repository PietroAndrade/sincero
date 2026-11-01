"""ITBI, deed and registry costs."""
from __future__ import annotations

from .inputs import SimulationInput


class ClosingCosts:
    def __init__(self, inp: SimulationInput):
        self.itbi = inp.list_price * inp.itbi_pct / 100.0
        self.registry = inp.list_price * inp.registry_pct / 100.0

    @property
    def total(self) -> float:
        return self.itbi + self.registry
