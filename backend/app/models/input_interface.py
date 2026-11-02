"""
The contract every simulation input must honour.

`SimulationInputInterface` is a pure interface: an ABC made only of abstract methods. It
holds no data — the values live in the DTOs of `input_dto.py`, which the interface hands
out through `contract()`, `market()` and `bank_credit()`. On top of those it promises the
derived amounts several components share and the two behaviours the application relies
on: `validate()` and `with_overrides()`.

Validators, the simulator and the what-if helpers are typed against this interface, so
an alternative implementation (a Flask request wrapper, a stub in a test) is accepted
everywhere as long as it implements these methods.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .input_dto import BankCreditData, ContractData, MarketData


class SimulationInputInterface(ABC):
    # ----- the data, by responsibility ------------------------------------
    @abstractmethod
    def contract(self) -> ContractData:
        """The contract with the developer: property, down payment and how it is paid."""

    @abstractmethod
    def market(self) -> MarketData:
        """Rates, financing term, closing-cost percentages and the income ceiling."""

    @abstractmethod
    def bank_credit(self) -> BankCreditData:
        """Pre-approved credit and the pro-soluto term."""

    # ----- derived amounts shared by several components -------------------
    @abstractmethod
    def required_down_payment(self) -> float:
        """Down payment demanded by the developer: `list_price × down_payment_pct`."""

    @abstractmethod
    def upfront(self) -> float:
        """Everything paid at signing (FGTS + cash)."""

    @abstractmethod
    def remaining_down_payment(self) -> float:
        """Down payment still owed to the developer after the upfront credits (never negative)."""

    # ----- behaviour ------------------------------------------------------
    @abstractmethod
    def validate(self) -> "SimulationInputInterface":
        """Raise `SimulationError` if the inputs describe an impossible contract; return self otherwise."""

    @abstractmethod
    def with_overrides(self, **overrides: Any) -> "SimulationInputInterface":
        """A copy with some fields changed (any field of any DTO) — the basis of every what-if."""
