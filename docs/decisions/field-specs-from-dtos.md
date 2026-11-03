# Decision: the API's field specs are derived from the DTOs, and `GET /api/fields` is their projection

*Status: accepted on 2026-11-03, implemented in `app/controllers/api_requests.py`
(`FieldSpec`, `FIELD_SPECS`, `field_specs()`), pinned by `tests/test_api_requests.py`. The
Flask route `GET /api/fields` itself is milestone 5. Since
[input-fields-from-proto](input-fields-from-proto.md) the DTOs' fields are themselves generated from
`backend/proto/sincero/simulation_input.proto`; the specs still read the DTOs, so the chain is
`.proto` → DTOs → `FieldSpec` → `/api/fields`, with the CLI reading the same DTOs.*

## Context

The [API contract](../api-contract.md) has a shape layer: before the model runs, a `POST` body
is checked for unknown keys, missing required keys, strict JSON types (`number`, `integer`,
`number|null`, `integer[]`, `string`), `null` only where allowed, finiteness and the API limits —
each with a stable `code` and the offending `field`. Those checks need, for every input
field, its **wire type**, whether it is **required**, whether it is **nullable** and its
**default**.

The same four facts are what `GET /api/fields` publishes so a front-end can build the form
without re-declaring defaults — the contract's "the API's `--help`". And they already exist
once, as the annotations and defaults of the three frozen DTOs in `app/models/input_dto.py`:

```python
@dataclass(frozen=True)
class ContractData:
    name: str
    list_price: float
    months_remaining: int
    down_payment_pct: float = 20.0
    developer_installment: Optional[float] = None
    balloon_months: tuple[int, ...] = field(default_factory=tuple)
```

The CLI already reads `field_defaults()` from these DTOs for `--help`; the contract says
"Defaults are **not** repeated in the controller". The question was whether the API's shape
layer would hold a second table of the fields — name, type, required, default — or read the
DTOs too.

## Decision

1. **One `FieldSpec` per DTO field, built from the DTO at import time.** `FieldSpec` is a
   small frozen dataclass: `name`, `group`, `type`, `required`, `default`, `unit`. `type` is
   mapped from the annotation (`str` → `string`, `float` → `number`, `int` → `integer`,
   `Optional[float]` → `number|null`, `tuple[int, ...]` → `integer[]`); `required` is "has no
   default", with `name` treated as defaulting to `"CUSTOM"` as the CLI does; `group` is the
   owning DTO (`contract` | `market` | `bank_credit`); `default` is `field_defaults()`'s.
   An annotation the mapping does not know is a `TypeError` at import — a new field with a
   new kind of type cannot slip into the API unspecified.
2. **The shape layer walks `FIELD_SPECS`, in DTO order.** Unknown keys are "not in
   `SPEC_BY_NAME`"; required keys are `REQUIRED_FIELDS`; each value is checked by its spec's
   `kind` and `nullable`; and "field by field in the order of the request table" is simply the
   order of the tuple. The layer has no per-field `if` chains.
3. **`GET /api/fields` is `[spec.to_dict() for spec in FIELD_SPECS]`.** Nothing is computed for
   the route that the checks did not already need. The one thing the DTOs do not carry is the
   **unit** (`R$`, `months`, `% per year`), which is presentation; it lives in a small `UNITS`
   table next to the specs until the open question of `dataclasses.field(metadata=…)` is
   settled, at which point the table disappears and the spec reads the metadata.
4. **Only the API limits are declared in the controller** (`UPPER_BOUNDS`, `MAX_BALLOONS`,
   `MAX_ITEMS`). They are protective ceilings the model does not have and should not have (a
   600-month term is not a business rule), so they are the controller's by the contract's own
   reasoning. A test asserts that every numeric field has either an API ceiling or a model
   bound (`income_commitment_ratio`, bounded to 0–1 by the model, is the one exception), so
   adding a numeric field forces a decision.

## Reason

- **Three readers, one source.** The CLI's `--help`, the API's shape checks and the API's
  `/api/fields` all describe the same sixteen fields. With a second table, a new DTO field
  would be accepted by `SimulationInput.from_dict`, shown by the CLI, and *rejected by the API
  as an unknown field* until someone remembered the table — the exact "silently out of sync"
  failure the contract's "defaults are not repeated" rule exists to prevent. Derived specs
  cannot drift: `test_field_specs_cover_every_model_field_in_dto_order` pins
  `[s.name for s in field_specs()] == field_names()`.
- **The types are already there.** The annotations are the model's statement of what each
  field is. Mapping `int` to "a JSON number with no fractional part" and `Optional[float]` to
  "`null` allowed" is a translation of that statement, not a new one. It also settles, without
  a separate rule, *why* only `developer_installment` and `pre_approved_credit` accept
  `null`: they are the two `Optional` fields.
- **`/api/fields` becomes free and trustworthy.** The contract promises that the form and the
  CLI "describe the same defaults from the same source". Reading the specs the checks use is
  the strongest form of that promise: what the route says is accepted *is* what the checks
  accept, because it is the same object.
- **The dependency direction holds.** `controllers → views → models`: the controller reads the
  model's DTOs (`fields()`, `get_type_hints()`) and adds the wire vocabulary. Nothing in the
  model learns about JSON, and the DTOs are not decorated for the API's sake.
- **Strictness is easier to get right once.** The contract's type rules have traps — JSON
  `true` is an `int` to Python, `19.0` is an integer but `19.5` is not, a 400-digit integer is
  finite but not representable as a float. Handling them per spec `kind` in one place
  (`_check_number`, `_check_integer`) is how a body with `"months_remaining": true` becomes a
  `400` instead of a silently simulated 1-month contract
  (`test_input_from_dict_alone_lets_the_body_through_but_the_layer_rejects_it`).

## Rejected alternatives

| Alternative | Why not |
|---|---|
| A hand-written field table in the controller (name, type, required, default) | a second source of truth for the facts the DTOs already state; drifts on the next DTO change; the contract forbids repeating defaults |
| A JSON Schema for the body, validated by a library | a third representation of the fields, a dependency, and error bodies that are not the contract's (`code`, `field`, `index`, the fixed order of checks) — the order in particular is hard to get from a generic validator |
| Annotating the DTOs with wire metadata (`field(metadata={"type": "number", "unit": "R$"})`) | puts JSON vocabulary in the model; the type is already in the annotation. Kept as the likely home for `unit` and help text only, per the contract's open question |
| No `FieldSpec` — the checks read `dataclasses.fields()` directly each time | the same derivation, scattered across the checks and `/api/fields`; the spec is the one place the annotation → wire-type mapping is written down and tested |
| Deriving the API limits from the DTOs too | the DTOs have no upper bounds and should not: the limits are not business rules |

## Consequences

- Adding a field to a DTO adds it to the CLI, the shape checks and `/api/fields` at once. The
  only manual steps are a unit in `UNITS` (optional) and an entry in `UPPER_BOUNDS` if it is
  numeric and unbounded by the model — a test fails until that is decided.
- Changing a field's annotation changes what the API accepts. `Optional[float]` → `float` on
  `developer_installment` would make `null` a `400` on the next request; that is intended.
- `name`'s default stays in the controller (`DEFAULT_NAME = "CUSTOM"`), the same place the CLI
  holds it. If it moves into `ContractData` ([open question](../api-contract.md#open-questions)),
  `FieldSpec` picks it up from `field_defaults()` and the special case goes away.
- `GET /api/fields` can list exactly what the contract's example shows, in DTO order, with the
  same `type` strings the error messages use (`must be an integer`, `must be a number`).
- The contract's open question on `input_from_dict` strictness is confirmed: under the shape
  layer its `int(m)` coercion of `balloon_months` is dead code, since items reach it as ints.
