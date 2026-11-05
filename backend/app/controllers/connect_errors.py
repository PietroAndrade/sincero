"""
The errors of the Connect service as `ConnectError`s (docs/api-contract.md, "Errors";
docs/decisions/api-protocol-and-language.md, question 2).

    a `buf.validate` rule of the request    invalid_argument + google.rpc.BadRequest
                                            (one field violation per rule broken)
    a rule of the model (`SimulationError`) invalid_argument + google.rpc.ErrorInfo
                                            (reason `invalid_input`, domain `sincero`; the model's
                                            message verbatim; `index` of the candidate, variation or
                                            rung in `metadata` when the request has several)
    an unknown simulation id                not_found

A client tells the two `invalid_argument`s apart by the detail: `BadRequest` marks a field,
`ErrorInfo` shows a message. `failed_precondition` is not used: no rule depends on the state of
the service, so a retry cannot succeed.

    validate(request)                     protovalidate -> BadRequest
    simulate_one(input)                   the model -> ErrorInfo
    simulate_all(inputs)                  ... with the index of the first input that fails
    model_error / validation_error / not_found     the mappings themselves

No Connect server in here yet (milestone 5); the service implementation calls these.
"""
from __future__ import annotations

from typing import Optional, Sequence

import protovalidate
from connectrpc.code import Code
from connectrpc.errors import ConnectError

from app.gen.google.rpc.error_details_pb import BadRequest, ErrorInfo
from app.models import SimulationError, SimulationInput, SimulationResult, simulate

DOMAIN = "sincero"
INVALID_INPUT = "invalid_input"     # ErrorInfo.reason of a model rule (the REST contract's 422 `code`)


# ----- the mappings ------------------------------------------------------------------------------
def model_error(exc: SimulationError, index: Optional[int] = None) -> ConnectError:
    """A rule of the model: `invalid_argument`, its message verbatim, an `ErrorInfo`."""
    metadata = {} if index is None else {"index": str(index)}
    info = ErrorInfo(reason=INVALID_INPUT, domain=DOMAIN, metadata=metadata)
    return ConnectError(Code.INVALID_ARGUMENT, str(exc), details=[info])


def field_path(violation) -> str:
    """`variations[0].months_remaining`, from a `buf.validate.FieldPath`; "" for a message rule."""
    path = violation.proto.field                 # None (protobuf-py: unset) for a message-level rule
    out = ""
    for element in (path.elements if path is not None else ()):
        out += ("." if out else "") + element.field_name
        subscript = element.subscript
        if subscript is not None:
            out += f"[{subscript.value!r}]" if isinstance(subscript.value, str) else f"[{subscript.value}]"
    return out


def validation_error(exc: protovalidate.ValidationError) -> ConnectError:
    """Rules of the `.proto`: `invalid_argument`, a `BadRequest` with one violation per rule broken."""
    violations = [BadRequest.FieldViolation(field=field_path(v), description=v.proto.message, reason=v.proto.rule_id)
                  for v in exc.violations]
    message = "; ".join(f"{fv.field}: {fv.description}" if fv.field else fv.description for fv in violations)
    return ConnectError(Code.INVALID_ARGUMENT, message, details=[BadRequest(field_violations=violations)])


def not_found(simulation_id: str) -> ConnectError:
    return ConnectError(Code.NOT_FOUND, f"simulation not found: {simulation_id}")


# ----- what the service calls --------------------------------------------------------------------
def validate(request) -> None:
    """Every `buf.validate` rule of the request message, or a `BadRequest`."""
    try:
        protovalidate.validate(request)
    except protovalidate.ValidationError as exc:
        raise validation_error(exc) from exc


def simulate_one(inp: SimulationInput) -> SimulationResult:
    """Run the model; a `SimulationError` becomes an `invalid_argument` with an `ErrorInfo`."""
    try:
        return simulate(inp)
    except SimulationError as exc:
        raise model_error(exc) from exc


def simulate_all(inputs: Sequence[SimulationInput]) -> list[SimulationResult]:
    """
    Run every input in order; the first `SimulationError` ends the request, with its index.
    Nothing is returned unless every input simulates, so the caller stores all or nothing.
    """
    results = []
    for i, inp in enumerate(inputs):
        try:
            results.append(simulate(inp))
        except SimulationError as exc:
            raise model_error(exc, index=i) from exc
    return results
