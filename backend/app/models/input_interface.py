"""
The behavioural contract of a simulation input.

`SimulationInputInterface` is a pure interface: an ABC made only of abstract methods, with
no data and no accessors. It promises the two things the application *does* with an
input — check it (`validate`) and derive a what-if from it (`with_overrides`).

The data itself is not part of this contract. It lives in the DTOs of `input_dto.py`, which
the concrete `SimulationInput` exposes as plain dataclass fields and which every model
component receives directly (`DownPaymentPlan(contract, …)`, `CreditGap(bank_credit, …)`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SimulationInputInterface(ABC):
    @abstractmethod
    def validate(self) -> "SimulationInputInterface":
        """Raise `SimulationError` if the inputs describe an impossible contract; return self otherwise."""

    @abstractmethod
    def with_overrides(self, **overrides: Any) -> "SimulationInputInterface":
        """A copy with some fields changed (any field of any DTO) — the basis of every what-if."""
