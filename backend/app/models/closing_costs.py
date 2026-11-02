"""ITBI, deed and registry costs."""
from __future__ import annotations

from .input_interface import SimulationInputInterface


class ClosingCosts:
    def __init__(self, inp: SimulationInputInterface):
        price, market = inp.contract().list_price, inp.market()
        self.itbi = price * market.itbi_pct / 100.0
        self.registry = price * market.registry_pct / 100.0

    @property
    def total(self) -> float:
        return self.itbi + self.registry
