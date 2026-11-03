# Decision: the input fields are declared in a `.proto`, and the DTOs' fields are generated from it

*Status: accepted, implemented in `backend/proto/sincero/simulation_input.proto`,
`backend/tools/gen_dto.py` and the generated `backend/app/models/input_fields.py`; pinned by
`backend/tests/test_gen_dto.py`. Builds on [field-specs-from-dtos](field-specs-from-dtos.md),
which stands unchanged: the shape layer and `GET /api/fields` still read the DTOs.*

## Context

The sixteen input fields of a simulation — the body of `POST /api/simulations`, the CLI flags,
the rows of `GET /api/fields` — were declared as three frozen dataclasses in
`app/models/input_dto.py`. Every other reader derived from them, which kept one source, but
that source was Python: a TypeScript front-end (milestone 6) or any other client could not read
it. Protocol Buffers is the one schema language with a typed, language-neutral declaration that
such a client could share — and, as an earlier experiment with proto3's JSON mapping showed, the
wrong tool for validating requests against this contract (it accepts `"440000"` and `true` as
numbers, treats `null` as "unset", has no `required` and accepts camelCase aliases).

The question was how to make the field declaration language-neutral without giving up the
frozen dataclasses the whole model is built on (`replace`, `fields`, `asdict`, hashing, the
derived amounts on `ContractData`).

## Decision

1. **One `.proto`, one flat message.** `backend/proto/sincero/simulation_input.proto` declares
   `SimulationInput` with the sixteen fields in DTO order, plus the three other request bodies
   of the contract (`ComparisonRequest`, `WhatIfRequest`, `CashLadderRequest`) for completeness.
   The message is flat because the wire body is flat; the owning DTO is a **field option**,
   `(sincero.field).group`, not nesting.
2. **What proto3 cannot say goes in the option.** proto3 has no custom defaults and no
   `required`; the `(sincero.field)` option carries `default_number` / `default_integer` /
   `default_string` and `nullable`. The field's label says the rest: a plain scalar is
   required, an `optional` scalar must have a default or be `nullable` (the generator refuses
   one with neither), a `repeated` field is an empty tuple by default.
3. **The DTOs' fields are generated; the DTOs are not.** `tools/gen_dto.py` renders one frozen
   dataclass per group — `ContractFields`, `MarketFields`, `BankCreditFields` — into
   `app/models/input_fields.py`, marked generated. The hand-written `ContractData`,
   `MarketData` and `BankCreditData` in `input_dto.py` subclass them and add only the derived
   amounts. Nothing else in the code base changed: `INPUT_GROUPS`, `FIELD_OWNER`,
   `field_defaults()`, `SimulationInput`, the validators, the views and both controllers read
   the DTOs exactly as before.
4. **Generated code is committed and drift is a test failure.** `make dto` regenerates;
   `tests/test_gen_dto.py` asserts the committed file equals a fresh render, that `field_names()`
   is the `.proto`'s field order, and that each DTO subclasses its generated class. Editing the
   `.proto` without regenerating, or editing the generated file by hand, fails `make test`.
5. **The `.proto` is a build-time artefact.** `grpcio-tools` is a dev dependency; the runtime
   (`requirements.txt`) gains nothing and the model imports no protobuf. The request path keeps
   the hand-written shape layer of `api_requests.py`.

## Reason

- **One source, readable by every language.** Field names, types, defaults, nullability and
  grouping are stated once, in a format a TypeScript client, an OpenAPI generator or a gRPC
  surface can consume. The Python side is derived from it, as the CLI and the API were already
  derived from the DTOs.
- **The model keeps its shape.** Generating dataclass *fields* and subclassing them keeps
  everything the model relies on — frozen, hashable, `replace`-able, positional construction
  (`ContractData("RA", 440_000, 19)`), the derived properties on `ContractData` — and keeps
  domain logic out of the generator.
- **The conventions are enforced, not just written.** The generator refuses a field without a
  group, an `optional` without a meaning, a default of the wrong type, a required field after
  an optional one and a type it does not map, each with a message naming the field. The
  dataclass module would have rejected some of these at import, later and less clearly.
- **Nothing moves at runtime.** The payload of `python cli.py … --json` and the rows of
  `field_specs()` are byte-for-byte what they were; all 204 unit tests and 54 scenarios pass
  unchanged, with the new tests on top.

## Rejected alternatives

| Alternative | Why not |
|---|---|
| Use the protoc-generated `_pb2` message classes as the DTOs | mutable, unhashable, zero-valued rather than defaulted, no `Optional` semantics without `HasField`, no place for the derived amounts; every model component, `replace()` and `asdict()` would change |
| Nest three messages (`contract`, `market`, `bank_credit`) inside `SimulationInput` | a natural proto shape, but its JSON form is not the contract's flat body; the grouping is a model concern and the contract says it is "not visible on the wire" |
| Keep hand-written DTOs and test them against the `.proto` | two declarations of every field, kept equal by a test, instead of one declaration and a derivation |
| Move `name`'s default (`"CUSTOM"`) into the `.proto` now | a default on the first field would force it after `list_price` and `months_remaining` in the dataclass, changing the positional signature and the order of `/api/fields`; the contract's open question stays open, recorded in the field's comment |
| Carry units and help text in the `.proto` too | the contract's open question on `field(metadata=…)`; it touches both controllers and is a separate decision. The `.proto` carries what the DTOs carry, no more |
| Use the `.proto` to validate requests (`json_format.ParseDict`) | proto3's JSON mapping accepts strings and `true` as numbers, `null` as "unset" (indistinguishable from omitted — the contract's `null_not_allowed`), has no `required`, no API limits, and accepts camelCase aliases; its one `ParseError` carries no code. The shape layer meets every `400` rule today with no dependency |

## Consequences

- Adding a field: one line in the `.proto`, `make dto`, commit both. Then, as before, a `UNITS`
  / `UPPER_BOUNDS` entry in `api_requests.py` (a test fails until the ceiling is decided) and a
  flag + help text in `cli_controller.py`.
- Changing a default or making a field nullable is a `.proto` edit; the generated file and
  therefore the CLI `--help`, `/api/fields` and the shape checks follow.
- `app/models/input_fields.py` is generated: never edited by hand, reviewed as the output of
  the `.proto` diff next to it.
- `grpcio-tools` (and its `protobuf` runtime) joins `requirements-dev.txt`; the `pre-push` hook's
  `make test` needs it installed in `backend/.venv`.
- The `.proto` is ready for a TypeScript client or an OpenAPI component to be generated from
  it when milestone 6 needs them; that generation is not part of this decision.
