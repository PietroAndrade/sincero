"""ITBI, deed and registry costs."""
from __future__ import annotations

from .input_dto import MarketData


class ClosingCosts:
    def __init__(self, list_price: float, market: MarketData):
        self.itbi = list_price * market.itbi_pct / 100.0
        self.registry = list_price * market.registry_pct / 100.0

    @property
    def total(self) -> float:
        return self.itbi + self.registry
