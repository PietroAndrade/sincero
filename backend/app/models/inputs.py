"""Input model of a simulation: the immutable composition of the three input DTOs."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from typing import Any, Mapping

from .input_dto import FIELD_OWNER, BankCreditData, ContractData, MarketData
from .input_interface import SimulationInputInterface
from .validators import InputValidator, default_validator


class SimulationInput(SimulationInputInterface):
    """
    Everything a simulation needs: a `ContractData`, a `MarketData` and a `BankCreditData`.

    It owns no values of its own. It composes the DTOs, derives the amounts several
    components share, applies the validation policy and builds what-if copies. Immutable:
    change it only through `with_overrides()`.
    """

    __slots__ = ("_contract", "_market", "_bank_credit")

    def __init__(self, contract: ContractData, market: MarketData = MarketData(),
                 bank_credit: BankCreditData = BankCreditData()):
        object.__setattr__(self, "_contract", contract)
        object.__setattr__(self, "_market", market)
        object.__setattr__(self, "_bank_credit", bank_credit)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SimulationInput":
        """
        Build from a flat `field -> value` mapping (a JSON body, parsed CLI flags). Each
        field is routed to the DTO that owns it; an unknown field is a `TypeError`.
        """
        grouped = cls._group(data)
        return cls(ContractData(**grouped[ContractData]), MarketData(**grouped[MarketData]),
                   BankCreditData(**grouped[BankCreditData]))

    def to_dict(self) -> dict[str, Any]:
        """The flat `field -> value` mapping, inverse of `from_dict`."""
        return {**asdict(self._contract), **asdict(self._market), **asdict(self._bank_credit)}

    # ----- SimulationInputInterface: the data --------------------------------
    def contract(self) -> ContractData:
        return self._contract

    def market(self) -> MarketData:
        return self._market

    def bank_credit(self) -> BankCreditData:
        return self._bank_credit

    # ----- SimulationInputInterface: derived amounts -------------------------
    def required_down_payment(self) -> float:
        return self._contract.list_price * self._contract.down_payment_pct / 100.0

    def upfront(self) -> float:
        return self._contract.fgts_upfront + self._contract.cash_upfront

    def remaining_down_payment(self) -> float:
        return max(0.0, self.required_down_payment() - self.upfront())

    # ----- SimulationInputInterface: behaviour -------------------------------
    def validate(self, validator: InputValidator | None = None) -> "SimulationInput":
        """
        Apply the validation policy (by default every rule in `validators.DEFAULT_VALIDATORS`)
        and return self, so callers can chain: `OffPlanSimulator(inp.validate())`.
        """
        (validator or default_validator()).validate(self)
        return self

    def with_overrides(self, **overrides: Any) -> "SimulationInput":
        """A copy with some fields changed — the basis of every what-if."""
        grouped = self._group(overrides)
        return SimulationInput(
            replace(self._contract, **grouped[ContractData]),
            replace(self._market, **grouped[MarketData]),
            replace(self._bank_credit, **grouped[BankCreditData]),
        )

    # ----- plumbing ------------------------------------------------------------
    @staticmethod
    def _group(data: Mapping[str, Any]) -> dict[type, dict[str, Any]]:
        unknown = sorted(set(data) - set(FIELD_OWNER))
        if unknown:
            raise TypeError(f"unknown simulation input field(s): {', '.join(unknown)}")
        grouped: dict[type, dict[str, Any]] = defaultdict(dict)
        for name, value in data.items():
            grouped[FIELD_OWNER[name]][name] = value
        return grouped

    def _parts(self) -> tuple[ContractData, MarketData, BankCreditData]:
        return self._contract, self._market, self._bank_credit

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable — use with_overrides()")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable — use with_overrides()")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SimulationInput) and self._parts() == other._parts()

    def __hash__(self) -> int:
        return hash(self._parts())

    def __repr__(self) -> str:
        return f"SimulationInput({self._contract!r}, {self._market!r}, {self._bank_credit!r})"
