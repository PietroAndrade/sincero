"""
The request side of the HTTP API: from a parsed JSON body to simulations that can run.

This is the "shape layer" of `docs/api-contract.md`. It answers one question for each of
the four `POST` bodies — can this become a simulation? — in two passes:

    400  shape rules    the body is an object, carries only input fields, the required ones
                        are present, every value has the strict JSON type of its field, is
                        finite, is `null` only where `null` is allowed, and is within the
                        API limits. Checked here, in the contract's order, so the same bad
                        body always gets the same answer.
    422  the model      the merged, resolved input describes a possible contract. Decided
                        by `simulate` (`SimulationError`), mapped here to the error body.

Every failure is an `ApiError` carrying the status and the contract's error body
(`error`, `code`, `field`, `index`). No Flask in this module: the controller parses the
body and maps `ApiError` to a response; everything in between is plain Python, and the
tests drive it with dicts.

    simulation_input(body)              POST /api/simulations
    comparison_inputs(body)             POST /api/comparisons              (base + candidates)
    what_if_inputs(body, base)          POST /api/simulations/{id}/what-if (variations)
    cash_ladder_inputs(body, base)      POST /api/simulations/{id}/cash-ladder (amounts)
    simulate_one(input) / simulate_all(inputs)                              the 422 pass

Field names, types and defaults are read from the model DTOs (`input_dto.py`, generated from
`proto/sincero/simulation_input.proto`), never re-declared; only the API limits — protective ceilings the model does not have — live here.
"""
from __future__ import annotations

import math
import sys
from dataclasses import MISSING, dataclass, fields as dataclass_fields
from typing import Any, Collection, Mapping, Optional, get_args, get_origin, get_type_hints

from app.models import (BankCreditData, ContractData, MarketData, SimulationError, SimulationInput, SimulationResult,
                        field_defaults, simulate)
from app.models.input_dto import INPUT_GROUPS
from app.views import input_from_dict

# ----- the error body ---------------------------------------------------------------
class ApiError(Exception):
    """A request the API refuses: HTTP status plus the contract's error body."""

    def __init__(self, status: int, code: str, message: str, *,
                 field: Optional[str] = None, index: Optional[int] = None):
        super().__init__(message)
        self.status, self.code, self.message, self.field, self.index = status, code, message, field, index

    def to_dict(self) -> dict:
        body: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.field is not None:
            body["field"] = self.field
        if self.index is not None:
            body["index"] = self.index
        return body

    def __repr__(self) -> str:
        return f"ApiError({self.status}, {self.to_dict()!r})"


def _bad_request(code: str, message: str, field: Optional[str] = None, index: Optional[int] = None) -> ApiError:
    return ApiError(400, code, message, field=field, index=index)


# ----- the input fields, read from the DTOs ----------------------------------------
DEFAULT_NAME = "CUSTOM"   # the one default the model does not hold (as in the CLI)

GROUP_NAMES: dict[type, str] = {ContractData: "contract", MarketData: "market", BankCreditData: "bank_credit"}

UNITS: dict[str, Optional[str]] = {
    "name": None, "list_price": "R$", "months_remaining": "months", "down_payment_pct": "% of list price",
    "fgts_upfront": "R$", "cash_upfront": "R$", "developer_installment": "R$ per month",
    "balloon_months": "months", "incc_rate_pa": "% per year", "bank_rate_pa": "% per year",
    "term_months": "months", "itbi_pct": "% of list price", "registry_pct": "% of list price",
    "income_commitment_ratio": "ratio 0-1", "pre_approved_credit": "R$", "pro_soluto_months": "months",
}

# API limits (docs/api-contract.md, "API limits"): upper bounds that keep one request bounded
# in time and size. The model bounds inputs from below; these are not business rules.
MAX_MONTHS = 600
MAX_MONEY = 10**12
MAX_PERCENT = 1000
MAX_BALLOONS = 60
MAX_ITEMS = 20            # candidates, variations, amounts (and ids)
MIN_ITEMS = 1

UPPER_BOUNDS: dict[str, int] = {
    "months_remaining": MAX_MONTHS, "term_months": MAX_MONTHS, "pro_soluto_months": MAX_MONTHS,
    "list_price": MAX_MONEY, "fgts_upfront": MAX_MONEY, "cash_upfront": MAX_MONEY,
    "developer_installment": MAX_MONEY, "pre_approved_credit": MAX_MONEY,
    "down_payment_pct": MAX_PERCENT, "itbi_pct": MAX_PERCENT, "registry_pct": MAX_PERCENT,
    "incc_rate_pa": MAX_PERCENT, "bank_rate_pa": MAX_PERCENT,
}
# `income_commitment_ratio` has no API ceiling: the model already bounds it to 0..1.


@dataclass(frozen=True)
class FieldSpec:
    """One input field as the API sees it: the row of `GET /api/fields`."""

    name: str
    group: str
    type: str            # string | number | integer | number|null | integer[]
    required: bool
    default: Any
    unit: Optional[str]

    @property
    def nullable(self) -> bool:
        return self.type.endswith("|null")

    @property
    def kind(self) -> str:
        """The type without the `|null`: what a non-null value must be."""
        return self.type.removesuffix("|null")

    def to_dict(self) -> dict:
        return {"name": self.name, "group": self.group, "type": self.type,
                "required": self.required, "default": self.default, "unit": self.unit}


def _json_type(hint: Any) -> str:
    """The wire type of a DTO annotation."""
    if hint is str:
        return "string"
    if hint is float:
        return "number"
    if hint is int:
        return "integer"
    args = get_args(hint)
    if get_origin(hint) is tuple and args and args[0] is int:
        return "integer[]"
    if type(None) in args:                               # Optional[X]
        inner = [a for a in args if a is not type(None)]
        if len(inner) == 1:
            return f"{_json_type(inner[0])}|null"
    raise TypeError(f"no JSON type for DTO annotation {hint!r}")


def _build_specs() -> tuple[FieldSpec, ...]:
    defaults = {**field_defaults(), "name": DEFAULT_NAME}
    specs = []
    for dto in INPUT_GROUPS:
        hints = get_type_hints(dto)
        for f in dataclass_fields(dto):
            default = defaults.get(f.name, MISSING)
            if default is MISSING and f.default_factory is not MISSING:   # balloon_months: tuple()
                default = list(f.default_factory())
            specs.append(FieldSpec(name=f.name, group=GROUP_NAMES[dto], type=_json_type(hints[f.name]),
                                   required=default is MISSING, default=None if default is MISSING else default,
                                   unit=UNITS.get(f.name)))
    return tuple(specs)


FIELD_SPECS: tuple[FieldSpec, ...] = _build_specs()
SPEC_BY_NAME: dict[str, FieldSpec] = {s.name: s for s in FIELD_SPECS}
REQUIRED_FIELDS: tuple[str, ...] = tuple(s.name for s in FIELD_SPECS if s.required)
NULLABLE_FIELDS: tuple[str, ...] = tuple(s.name for s in FIELD_SPECS if s.nullable)


def field_specs() -> list[dict]:
    """`GET /api/fields`: every input field, in DTO order, with its type, default and unit."""
    return [s.to_dict() for s in FIELD_SPECS]


# ----- JSON value helpers --------------------------------------------------------------
def _describe(value: Any) -> str:
    """The JSON type of a parsed value, for `got …` messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, list):
        return "an array"
    if isinstance(value, dict):
        return "an object"
    return type(value).__name__


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite(value: Any) -> bool:
    """Finite, and representable as a finite float (a 400-digit integer is not)."""
    if isinstance(value, float):
        return math.isfinite(value)
    return abs(value) <= sys.float_info.max


def _not_null(value: Any, path: str, index: Optional[int]) -> None:
    """`null` in an item position (an amount, a candidate, a balloon month) is never a value."""
    if value is None:
        raise _bad_request("null_not_allowed", f"{path} must not be null", path, index)


def _check_number(value: Any, path: str, index: Optional[int] = None) -> float:
    """Strict JSON number, finite. Returns it as a float (the normalised form)."""
    _not_null(value, path, index)
    if not _is_number(value):
        raise _bad_request("wrong_type", f"{path} must be a number, got {_describe(value)}", path, index)
    if not _is_finite(value):
        raise _bad_request("not_finite", f"{path} must be a finite number", path, index)
    return float(value)


def _check_integer(value: Any, path: str, index: Optional[int] = None) -> int:
    """A JSON number with no fractional part (`19` or `19.0`, never `19.5`). Returns an int."""
    _not_null(value, path, index)
    if not _is_number(value):
        raise _bad_request("wrong_type", f"{path} must be an integer, got {_describe(value)}", path, index)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _bad_request("not_finite", f"{path} must be a finite number", path, index)
        if not value.is_integer():
            raise _bad_request("wrong_type", f"{path} must be an integer, got {value!r}", path, index)
        return int(value)
    return value


def _check_upper_bound(value: Any, name: str, path: str, index: Optional[int] = None) -> None:
    limit = UPPER_BOUNDS.get(name)
    if limit is not None and value > limit:
        raise _bad_request("out_of_range", f"{path} must be at most {limit:,}", path, index)


# ----- one input field ---------------------------------------------------------------
def _check_field(spec: FieldSpec, value: Any, path: str, index: Optional[int], null_hint: str) -> Any:
    """
    Rules 4–7 of the contract for one field: `null` (`null_not_allowed`), type (`wrong_type`),
    finiteness (`not_finite`), limits (`out_of_range`). Returns the normalised value:
    floats for numbers, ints for integers, a list of ints for `balloon_months`.
    """
    if value is None:
        if spec.nullable:
            return None
        raise _bad_request("null_not_allowed", f"{path} must not be null; {null_hint}", path, index)
    kind = spec.kind
    if kind == "string":
        if not isinstance(value, str):
            raise _bad_request("wrong_type", f"{path} must be a string, got {_describe(value)}", path, index)
        return value
    if kind == "number":
        number = _check_number(value, path, index)
        _check_upper_bound(value, spec.name, path, index)
        return number
    if kind == "integer":
        integer = _check_integer(value, path, index)
        _check_upper_bound(integer, spec.name, path, index)
        return integer
    if kind == "integer[]":
        if not isinstance(value, list):
            raise _bad_request("wrong_type", f"{path} must be an array of integers, got {_describe(value)}", path, index)
        if len(value) > MAX_BALLOONS:
            raise _bad_request("out_of_range", f"{path} must have at most {MAX_BALLOONS} items", path, index)
        return [_check_integer(item, f"{path}[{i}]", index) for i, item in enumerate(value)]
    raise AssertionError(f"unhandled field type {spec.type}")   # pragma: no cover


# ----- a flat set of input fields ---------------------------------------------------------
def _check_fields(data: Mapping[str, Any], *, prefix: str = "", index: Optional[int] = None,
                  required: tuple[str, ...] = (), present: Optional[Collection[str]] = None,
                  null_hint: str = "omit it to use the default") -> dict[str, Any]:
    """
    Steps 5–7 of the contract on one object of input fields: unknown keys, required keys,
    then field by field in DTO order. `prefix` is the object's path (`base.`, `candidates[1].`)
    and `index` its position, so errors name the right place. `present` is where the
    required keys are looked for — the merged keys, for a candidate that inherits from `base`.
    """
    unknown = [key for key in data if key not in SPEC_BY_NAME]
    if unknown:
        where = f" in {prefix[:-1]}" if prefix else ""
        raise _bad_request("unknown_field", f"unknown simulation input field(s){where}: {', '.join(unknown)}",
                           f"{prefix}{unknown[0]}", index)
    present = data if present is None else present
    for name in required:
        if name not in present:
            raise _bad_request("missing_field", f"{prefix}{name} is required", f"{prefix}{name}", index)
    return {spec.name: _check_field(spec, data[spec.name], f"{prefix}{spec.name}", index, null_hint)
            for spec in FIELD_SPECS if spec.name in data}


def _resolve(data: Mapping[str, Any]) -> SimulationInput:
    """Defaults filled in, `null` meaning absent — the resolved input the id is derived from."""
    resolved = {**field_defaults(), "name": DEFAULT_NAME, **data}
    return input_from_dict(resolved)


def _require_object(body: Any) -> Mapping[str, Any]:
    if not isinstance(body, dict):
        raise _bad_request("wrong_type", f"request body must be a JSON object, got {_describe(body)}", "body")
    return body


def _check_wrapper(body: Mapping[str, Any], expected: tuple[str, ...]) -> None:
    """The keys of a comparison / what-if / ladder body: nothing outside `expected`."""
    unknown = [key for key in body if key not in expected]
    if unknown:
        raise _bad_request("unknown_field",
                           f"unknown key(s) in request body: {', '.join(unknown)}; expected {', '.join(expected)}",
                           unknown[0])


def _check_items(body: Mapping[str, Any], key: str, item_noun: str) -> list:
    """A required wrapper array of 1..MAX_ITEMS items."""
    if key not in body:
        raise _bad_request("missing_field", f"{key} is required", key)
    items = body[key]
    if items is None:
        raise _bad_request("null_not_allowed", f"{key} must not be null", key)
    if not isinstance(items, list):
        raise _bad_request("wrong_type", f"{key} must be an array of {item_noun}, got {_describe(items)}", key)
    if not MIN_ITEMS <= len(items) <= MAX_ITEMS:
        raise _bad_request("out_of_range", f"{key} must have between {MIN_ITEMS} and {MAX_ITEMS} items", key)
    return items


def _require_item_object(item: Any, path: str, index: int) -> Mapping[str, Any]:
    _not_null(item, path, index)
    if not isinstance(item, dict):
        raise _bad_request("invalid_value", f"{path} must be an object, got {_describe(item)}", path, index)
    return item


# ----- the four bodies ---------------------------------------------------------------------
def simulation_input(body: Any) -> SimulationInput:
    """
    `POST /api/simulations`: the flat input. Returns the resolved `SimulationInput`
    (defaults applied, numbers normalised) or raises a 400 `ApiError`.
    """
    data = _check_fields(_require_object(body), required=REQUIRED_FIELDS)
    return _resolve(data)


def comparison_inputs(body: Any) -> list[SimulationInput]:
    """
    `POST /api/comparisons`: `base` (optional) + `candidates` (1..20). Each candidate is
    `{**base, **candidate}` and must satisfy every rule of the flat input after the merge.
    Returns one resolved input per candidate, in order, or raises a 400 `ApiError`.
    """
    body = _require_object(body)
    base_data = body.get("base", {})
    if base_data is None:
        raise _bad_request("null_not_allowed", "base must not be null; omit it to share nothing", "base")
    if not isinstance(base_data, dict):
        raise _bad_request("wrong_type", f"base must be an object, got {_describe(base_data)}", "base")
    candidates = _check_items(body, "candidates", "objects")
    _check_wrapper(body, ("base", "candidates"))

    base = _check_fields(base_data, prefix="base.")
    inputs = []
    for i, item in enumerate(candidates):
        path = f"candidates[{i}]"
        candidate = _require_item_object(item, path, i)
        overrides = _check_fields(candidate, prefix=f"{path}.", index=i, required=REQUIRED_FIELDS,
                                  present=base.keys() | candidate.keys())
        inputs.append(_resolve({**base, **overrides}))
    return inputs


def what_if_inputs(body: Any, base: SimulationInput) -> list[SimulationInput]:
    """
    `POST /api/simulations/{id}/what-if`: `variations` (1..20 non-empty objects of input
    fields) applied to the stored base: `base.with_overrides(**variation)`. `null` on
    `developer_installment` / `pre_approved_credit` is a meaningful override (back to
    automatic sizing). Returns one input per variation, in order, or raises a 400 `ApiError`.
    """
    body = _require_object(body)
    variations = _check_items(body, "variations", "objects")
    _check_wrapper(body, ("variations",))

    inputs = []
    for i, item in enumerate(variations):
        path = f"variations[{i}]"
        variation = _require_item_object(item, path, i)
        if not variation:
            raise _bad_request("invalid_value", f"{path} is empty", path, i)
        overrides = _check_fields(variation, prefix=f"{path}.", index=i, null_hint="omit it to keep the base's value")
        inputs.append(base.with_overrides(**overrides))
    return inputs


def cash_ladder_amounts(body: Any) -> list[float]:
    """
    `POST /api/simulations/{id}/cash-ladder`: `amounts` (1..20), finite, >= 0, within the
    money limit, strictly increasing. Returns the amounts as floats or raises a 400 `ApiError`.
    """
    body = _require_object(body)
    raw = _check_items(body, "amounts", "numbers")
    _check_wrapper(body, ("amounts",))

    amounts: list[float] = []
    for i, value in enumerate(raw):
        path = f"amounts[{i}]"
        amount = _check_number(value, path, i)
        if amount < 0:
            raise _bad_request("out_of_range", f"amounts must not be negative: {path} = {value}", path, i)
        _check_upper_bound(value, "cash_upfront", path, i)
        if amounts and amount <= amounts[-1]:
            raise _bad_request("invalid_value",
                               f"amounts must be strictly increasing: {path} = {value} is not greater than amounts[{i - 1}]",
                               path, i)
        amounts.append(amount)
    return amounts


def cash_ladder_inputs(body: Any, base: SimulationInput) -> list[SimulationInput]:
    """The rungs of a ladder: `base.with_overrides(cash_upfront=a)` for each amount, in order."""
    return [base.with_overrides(cash_upfront=amount) for amount in cash_ladder_amounts(body)]


# ----- the 422 pass ---------------------------------------------------------------------------
def simulate_one(inp: SimulationInput) -> SimulationResult:
    """Run the model; a `SimulationError` becomes a 422 `ApiError` with the message verbatim."""
    try:
        return simulate(inp)
    except SimulationError as exc:
        raise ApiError(422, "invalid_input", str(exc)) from exc


def simulate_all(inputs: list[SimulationInput]) -> list[SimulationResult]:
    """
    Run every input in order; the first `SimulationError` ends the request with its `index`.
    Nothing is returned unless every input simulates, so the caller stores all or nothing.
    """
    results = []
    for i, inp in enumerate(inputs):
        try:
            results.append(simulate(inp))
        except SimulationError as exc:
            raise ApiError(422, "invalid_input", str(exc), index=i) from exc
    return results
