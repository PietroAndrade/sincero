"""
The scenario "world": collects what the Given steps say, performs the When, and keeps
what the Then steps need. Step definitions stay three or four lines because all the
bookkeeping lives here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .gateway import EngineGateway
from .metrics import Metric, parse_metric


@dataclass
class SimulationWorld:
    engine: EngineGateway
    market: dict[str, Any] = field(default_factory=dict)
    contract: dict[str, Any] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    result: Optional[dict] = None
    previous_result: Optional[dict] = None
    comparison: Optional[list[dict]] = None
    cash_ladder: Optional[list[dict]] = None
    error: Optional[str] = None

    # ----- lifecycle ------------------------------------------------------
    def reset(self) -> None:
        self.market, self.contract, self.candidates = {}, {}, []
        self.result = self.previous_result = self.comparison = self.cash_ladder = self.error = None

    # ----- givens ---------------------------------------------------------
    def set_market(self, incc_rate_pa: float, bank_rate_pa: float, term_months: int) -> None:
        self.market.update(incc_rate_pa=incc_rate_pa, bank_rate_pa=bank_rate_pa, term_months=term_months)

    def set_property(self, name: str, list_price: float, months_remaining: int) -> None:
        self.contract.update(name=name, list_price=list_price, months_remaining=months_remaining)

    def set(self, **fields: Any) -> None:
        """Any other SimulationInput field (down_payment_pct, fgts_upfront, ...)."""
        self.contract.update(fields)

    def set_candidates(self, rows: list[dict[str, Any]]) -> None:
        self.candidates = list(rows)

    # ----- whens ----------------------------------------------------------
    def input_data(self, **overrides: Any) -> dict:
        return {**self.market, **self.contract, **overrides}

    def run(self, **overrides: Any) -> None:
        self.error, self.result = None, None
        try:
            self.result = self.engine.simulate(self.input_data(**overrides))
        except self.engine.error_type as exc:
            self.error = str(exc)

    def rerun(self, **overrides: Any) -> None:
        self.previous_result = self.result
        self.run(**overrides)

    def compare_candidates(self) -> None:
        self.comparison = self.engine.compare([self.input_data(**c) for c in self.candidates])

    def compare_cash(self, amounts: list[float]) -> None:
        rows = self.engine.compare([self.input_data(cash_upfront=a) for a in amounts])
        self.cash_ladder = [{"cash": a, **row} for a, row in zip(amounts, rows)]

    # ----- thens ----------------------------------------------------------
    def current(self) -> dict:
        assert self.error is None, f"the simulation was rejected: {self.error}"
        assert self.result is not None, "the simulation was never run"
        return self.result

    def previous(self) -> dict:
        assert self.previous_result is not None, "there is no previous run to compare with"
        return self.previous_result

    def metric(self, metric: Metric | str) -> float:
        return self._as_metric(metric).read(self.current())

    def previous_metric(self, metric: Metric | str) -> float:
        return self._as_metric(metric).read(self.previous())

    @staticmethod
    def _as_metric(metric: Metric | str) -> Metric:
        return metric if isinstance(metric, Metric) else parse_metric(metric)
