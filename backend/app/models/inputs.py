"""Input model of a simulation: the three input DTOs, validated together and varied together."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from .input_dto import FIELD_OWNER, BankCreditData, ContractData, MarketData
from .input_interface import SimulationInputInterface
from .validators import DEFAULT_POLICY, ValidationPolicy


@dataclass(frozen=True)
class SimulationInput(SimulationInputInterface):
    """
    A `ContractData`, a `MarketData` and a `BankCreditData`. Components read the DTO they
    need (`inp.contract`, `inp.market`, `inp.bank_credit`); this class only adds what
    concerns the three together: validation, what-if copies and the flat `dict` form.
    """

    contract: ContractData
    market: MarketData = MarketData()
    bank_credit: BankCreditData = BankCreditData()

    # ----- SimulationInputInterface ------------------------------------------
    def validate(self, policy: ValidationPolicy = DEFAULT_POLICY) -> "SimulationInput":
        """Apply `policy` to each DTO (contract → market → bank credit) and return self."""
        policy.contract.validate(self.contract)
        policy.market.validate(self.market)
        policy.bank_credit.validate(self.bank_credit)
        return self

    def with_overrides(self, **overrides: Any) -> "SimulationInput":
        """A copy with some fields changed, whichever DTO owns them — the basis of every what-if."""
        grouped = _group(overrides)
        return replace(self,
                       contract=replace(self.contract, **grouped[ContractData]),
                       market=replace(self.market, **grouped[MarketData]),
                       bank_credit=replace(self.bank_credit, **grouped[BankCreditData]))

    # ----- flat form (JSON body, CLI flags) ------------------------------------
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SimulationInput":
        """Build from a flat `field -> value` mapping; each field goes to the DTO that owns it."""
        grouped = _group(data)
        return cls(ContractData(**grouped[ContractData]), MarketData(**grouped[MarketData]),
                   BankCreditData(**grouped[BankCreditData]))

    def to_dict(self) -> dict[str, Any]:
        """The flat `field -> value` mapping, inverse of `from_dict`."""
        return {**asdict(self.contract), **asdict(self.market), **asdict(self.bank_credit)}


def _group(data: Mapping[str, Any]) -> dict[type, dict[str, Any]]:
    """Split a flat mapping by owning DTO; an unknown field is a `TypeError`."""
    unknown = sorted(set(data) - set(FIELD_OWNER))
    if unknown:
        raise TypeError(f"unknown simulation input field(s): {', '.join(unknown)}")
    grouped: dict[type, dict[str, Any]] = defaultdict(dict)
    for name, value in data.items():
        grouped[FIELD_OWNER[name]][name] = value
    return grouped
