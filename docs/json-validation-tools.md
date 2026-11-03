# Can a JSON validation library replace the shape layer?

*Status: evaluated on 2026-11-03 against revision 6 of [`api-contract.md`](api-contract.md) and
the hand-written layer in `backend/app/controllers/api_requests.py`. Companion to
[`openapi-plan.md`](openapi-plan.md), whose decision 4 (hand-written YAML, verified by tests)
rests on this evaluation. Verdict: **none is adopted for the request path**; `jsonschema` is
used in tests only; protobuf was measured on two routes: it cannot be the validator, and it is adopted as the schema declaration (decision 3).
`jsonschema` and protobuf were run locally; marshmallow, pydantic and msgspec are assessed
from their documentation.*

## What the layer must do — the yardstick

The contract is unusually specific about *how* a bad body is refused, not only *that* it is.
A library is a fit only if it can meet these rows or be bent to them for less code than the
layer itself (≈440 lines with its docstrings, no dependency, 95 tests).

| # | Rule (contract section) | What it means for a tool |
|---|---|---|
| R1 | body must be an object; wrapper keys (`base`, `candidates`, `variations`, `amounts`) have fixed types and sizes | trivial everywhere |
| R2 | `list_price`, `months_remaining` required — **after** the `base` + candidate merge | merge first, validate after; any tool can |
| R3 | unknown keys rejected; `field` = the **first** unknown key in document order; message lists **all** | needs the unexpected keys as data, not as prose |
| R4 | strict JSON types: `"440000"` ✗, `true` ✗ for a number; `19.0` ✓ and `19.5` ✗ for an integer | no string coercion; `bool` is not a number (it is an `int` to Python); integer means "no fractional part" |
| R5 | `NaN`, `Infinity` rejected (`not_finite`) | JSON has no NaN, so no schema language has a keyword for it; Python's parser lets it in |
| R6 | `null` only on the two `Optional` fields; elsewhere `null_not_allowed` — a code of its own, distinct from `wrong_type` | the tool must tell "null" apart from "wrong type", or the caller must |
| R7 | API limits (`maximum`, `maxItems`, 1–20 items) | trivial everywhere |
| E1 | stable `code` per cause: `wrong_type`, `unknown_field`, `missing_field`, `null_not_allowed`, `not_finite`, `out_of_range`, `invalid_value` | the tool's error kinds must map 1:1 onto these |
| E2 | `field` as a path (`candidates[1].months_remaining`, `balloon_months[1]`) and `index` for items | structured error location |
| E3 | **one** error — the first in the contract's order: object → wrapper → unknown → required → fields in DTO order → (null, type, finite, limit) → per item | most tools collect *all* errors in *their* order; "first in ours" means sorting theirs |
| E4 | the two rules a schema cannot state: `amounts` strictly increasing; `{}` is not a variation | custom code in every case |
| S1 | the DTOs stay the **one** declaration of the fields ([decision](decisions/field-specs-from-dtos.md)) | a tool that wants its own model class per DTO fails this, unless it can read the dataclasses |
| S2 | no runtime dependency beyond Flask (the contract: "a missing dependency — there is none") | weight counts |

## The candidates

### marshmallow (3.x) — *not verified locally; from its documentation*

A `Schema` per DTO with `fields.Float`, `fields.Integer`, `fields.List`, `unknown=RAISE`,
`allow_none` on the two optional fields.

- R4: `Float` accepts `"440000"` (it calls `float()`), so strings pass unless every numeric
  field is declared `strict=True`; `Integer(strict=True)` then rejects `19.0` as well, which
  the contract accepts, while non-strict `Integer` **truncates `19.5` to `19`** silently. Booleans
  are refused by `Number`. Getting rule 4 exactly needs a custom `Integer` subclass.
- R5: `Float(allow_nan=False)` exists. ✓
- R6: `allow_none=False` yields "Field may not be null." — a distinct message, so a code can be
  derived by matching it. Fragile.
- R3/E2: unknown keys come as `{"fgts_upfrnt": ["Unknown field."]}` — keys are data ✓, order is
  the dict's ✓. Nested list errors carry the index ✓.
- E1/E3: errors are a dict of *all* failures keyed by field, messages are strings; codes come
  from overriding `error_messages` per field with the code as the message, then re-ordering by
  DTO order and picking the first. That re-implements E3 on top of the library.
- S1: a second declaration of every field (a `Schema` class per DTO). ✗ — the one thing the
  project's field decision forbids. `marshmallow-dataclass` can derive schemas from the
  dataclasses, which fixes S1 at the cost of one more package and its type-mapping opinions.
- S2: one pure-Python package. Acceptable.

**Verdict:** workable, but the adapter (strict numerics, code mapping, ordering, merge for
candidates) is about the size of the current layer, with a dependency and a second model.

### pydantic (v2) — *not verified locally; from its documentation*

The strongest candidate on paper: errors carry a machine `type` (`int_type`, `float_type`,
`extra_forbidden`, `missing`, `finite_number`, `less_than_equal`), a `loc` tuple (→ `field`
and `index`), `extra="forbid"`, `allow_inf_nan=False`, and `TypeAdapter(ContractData)` can
validate the **existing stdlib dataclasses** — so S1 can hold.

- R4: neither mode matches rule 4. *Lax* coerces `"440000"` → `440000.0` (✗) while accepting
  `19.0` for an int and refusing `19.5` (✓). *Strict* refuses the string (✓) but also refuses
  `19.0` for an int (✗). A custom `BeforeValidator` per numeric kind restores the contract's
  rule; that is the layer's `_check_number` / `_check_integer` again, as annotations.
- R6: `None` on a non-optional field is `int_type` / `float_type`, not a distinct kind; the
  caller infers `null_not_allowed` from `input == None`. Doable.
- E1: a mapping `type → code` of ~8 entries. ✓
- E3: `ValidationError.errors()` lists **every** failure in pydantic's order (fields in
  definition order, which is DTO order ✓; but `extra_forbidden` entries come last, where the
  contract wants unknown keys first). Sort by the contract's precedence, take the first.
- R2 after merge, E4: outside the model, as now.
- S2: pydantic + pydantic-core (compiled). The heaviest runtime addition on this list; Docker
  image and cold start notice it.

**Verdict:** the best-fitting library, and still an adapter of 80–120 lines plus the
dependency to land where the layer already is. Worth revisiting only if pydantic arrives for
another reason (e.g. the front-end wants its JSON Schema export).

### `jsonschema` (Draft 2020-12) — **verified locally, 4.25.1 is already installed**

Validate the body against the `SimulationInput` schema of `openapi.yaml` — the appeal is that
**the schema served at `/api/openapi.yaml` would be the validator**, no second declaration
(S1 ✓ via the drift guard that ties the schema to `FIELD_SPECS`).

Observed on the contract's traps:

| Body | Result |
|---|---|
| `true` for a number | rejected, `type` ✓ |
| `19.0` for an integer | accepted ✓ (JSON Schema's "mathematical integer") |
| `19.5` for an integer | rejected ✓ |
| `NaN` for a number | **accepted** ✗ (R5: no keyword exists; `maximum` catches `Infinity` only by accident, and only where a limit is declared) |
| `null` for `itbi_pct` | `type` error — indistinguishable from `"x"` (R6 ✗ without a post-check) |
| two unknown keys | one `additionalProperties` error; the keys appear **only in the message text** (R3: `field` would need a regex or a set difference done by hand) |
| several rules broken | `iter_errors` yields all; the order observed (`additionalProperties` → `required` → properties in schema order) happens to match steps 5–7 of the contract but is **not documented as stable** |

- E1: `error.validator` (`type`, `required`, `additionalProperties`, `maximum`, `maxItems`,
  `minItems`, `minProperties`) maps onto the codes. ✓
- E2: `error.absolute_path` → `candidates[1].months_remaining`. ✓
- E4 and the merge: outside, as now.
- S2: pure Python, already present as a transitive dependency — but "transitive" is not
  "declared"; it would have to be pinned.

**Verdict:** closer than marshmallow for less code, and the only option that validates with the
document the front-end reads. Still needs post-checks for R5 and R6, its own ordering, and a
parser for R3. **Adopted for tests only** (openapi-plan drift guards 5–7: examples and real
payloads validate against the schema), not for the request path, where the contract's
`not_finite` and `null_not_allowed` would become special cases bolted onto a generic error.

### Protocol Buffers (proto3 JSON mapping) — **measured**, `protobuf` 7.36.2, experiment in [`experiments/protobuf-validation/`](experiments/protobuf-validation/)

Kept as an option: it is the one candidate with a typed, language-neutral schema that a
TypeScript client could share, and the experiment shows exactly what it would cost. The
message mirrors the contract's table with every scalar `optional` (proto3 has no custom
defaults, so presence must be detectable to apply `20.0` afterwards) and the two nullable
fields as plain `optional double`; `ComparisonRequest` nests it for `base` + `candidates`.
`json_format.ParseDict` is the validator. Twenty-three bodies of the contract's `400` table
and the RA example, plus five nested ones, were run through it and through the layer
(`experiment.py`; output reproduced below).

**Where proto3 agrees with the contract** (12 of the 24 refusals — 11 for the contract's reason, one by coincidence, `2**31` — grouped in the 7 rows below, and every acceptance):

| Body | proto3 | Contract |
|---|---|---|
| `19.0` for an integer | accepted, `19` | ✓ |
| `19.5` for an integer | `Couldn't parse integer: 19.5 at SimulationInput.months_remaining` | ✓ `wrong_type` |
| `true` for an **integer** | `Bool value True is not acceptable for integer field` | ✓ |
| `NaN` / `Infinity` as parsed floats | `Couldn't parse NaN, use quoted "NaN" instead` | ✓ `not_finite` |
| `null` as a `balloon_months` item | `null is not allowed to be used as an element in a repeated field at …balloon_months[1]` | ✓ |
| unknown key, top level or in `candidates[1]` | `has no field named "foo" at "ComparisonRequest.candidates[1]"` | ✓, with a path |
| `candidates` is an object, not an array | `repeated field candidates must be in []` | ✓ |

**Where it contradicts the contract** — each is proto3 JSON *by design*, not a bug:

| Body | proto3 | Contract | Rule |
|---|---|---|---|
| `"440000"` for a number; `"19"` for an integer; `"12"` as a balloon item | **accepted**, coerced | `wrong_type` | R4 — the mapping's "either numbers or strings" |
| `true` for a **number** (`double`) | **accepted as `1.0`** | `wrong_type` | R4 — worse than a string: a silent value |
| `"NaN"` as a string | **accepted as NaN** | `wrong_type` | R5 — the quoted form is the mapping's own spelling of NaN |
| `list_price: 10**400` | `OverflowError` — a Python exception, not a `ParseError` | `not_finite` | R5 — would be a `500` |
| `itbi_pct: null` | **accepted**, field left unset — indistinguishable from omitted | `null_not_allowed` | R6 — `null` *is* "use the default" in proto3, the exact semantics rule 6 forbids |
| `months_remaining` omitted | accepted | `missing_field` | R2 — proto3 has no `required` |
| `months_remaining: 5000`; 61 balloon months; `candidates: []` | accepted | `out_of_range` | R7 — only `int32` overflow (`2**31`) is refused, with "Value out of range", a coincidence |
| `{"listPrice": 440000, "monthsRemaining": 19}` | **accepted** | `unknown_field` | R3 — the mapping accepts the camelCase spelling of every field, a second name per input the contract does not define |

**Error surface.** One `ParseError` per request — the *first* failure (E3 ✓, the only candidate
besides msgspec with first-error semantics). The location is in the message text
(`at ComparisonRequest.candidates[1].months_remaining`), parseable into `field` and `index`
(E2 ≈); there is no error kind (E1 ✗) — distinguishing `wrong_type` from `out_of_range` means
matching message prefixes (`Couldn't parse integer`, `has no field named`, `Value out of
range`…), which are not a stable API. The unknown-field message appends the whole list of
available fields, camelCase.

**Cost.** `grpcio-tools` (or a `protoc` binary) at build time, `protobuf` at runtime, a `.proto`
that re-declares the sixteen fields (S1 ✗ — a third declaration after the DTOs and the YAML),
and a generated `_pb2.py` pinned to the runtime's major version. Parsing the RA body took
34 µs against the layer's 26 µs — irrelevant next to ~3 ms to simulate, but not a gain either.

**What it would take to meet the contract:** a pre-pass over the raw body for R4 (reject
strings and booleans where numbers are expected — the layer's `_check_number`), a post-pass
for R2, R6 (impossible: `null` and omitted are the same message), R7 and the camelCase
spellings, and a message-prefix → `code` table. The pre-pass alone is the part of the layer
that carries the contract's hard rules; proto3 would validate only what is left.

**Verdict:** an option, measured, not adopted. It would be reconsidered if the API gained a
gRPC or binary surface where the `.proto` is the contract and the JSON form is secondary; for
a JSON resource API whose rule 4 is "strict JSON types", a mapping whose first design choice
is "strings are numbers" starts on the wrong side of the contract.

### msgspec — *not verified locally*

`msgspec.convert(body, ContractData, strict=True)` validates against the existing dataclasses
(S1 ✓), is strict by default (no `str` → number, `bool` is not a number ✓), reports **one**
error, the first in field-definition order (E3 ≈ ✓ — the only library with first-error
semantics). Unknown keys are **ignored** by default; `forbid_unknown_fields` is a `Struct`
option, so refusing them on the stdlib dataclasses (R3) needs a check of our own.

- R4: strict `int` refuses `19.0`; `strict=False` accepts it but also coerces strings. ✗ either way.
- R5: NaN passes (it is a float). ✗
- E1/E2: the location is in the message text (``"Expected `int`, got `float` - at `$.months_remaining`"``), no code object — parsing messages for codes and paths is the fragility
  marshmallow has, without marshmallow's per-field dict.

**Verdict:** attractive ergonomics, wrong error surface for a contract that promises codes.

### Others, briefly

| Tool | Why not |
|---|---|
| `fastjsonschema` | `jsonschema` compiled to Python with first-error semantics (closer to E3) and `.rule` / `.path` on the exception; same gaps as `jsonschema` (R5, R6, R3 as prose). Would add a dependency for speed the API does not need (~3 ms to simulate, validation is noise). |
| `cerberus`, `voluptuous`, `schema` | their own schema DSLs (a second declaration), coercion by default, messages rather than codes; cerberus has error codes but last released in 2021. |
| `attrs` + `cattrs` | structures into classes, coerces (`float("440000")`), exception groups rather than one coded error. |
| `connexion` (spec-first Flask/ASGI) | validates requests against `openapi.yaml` and routes from it — the most "one source" option — but its `400` body is RFC 7807 (`{"type","title","detail","status"}`), its order is the validator's, and it takes over the app (routing, error handlers, the `HTTPException` → JSON rewrite the contract specifies). Adopting it would mean rewriting the error section of the contract to connexion's shape. |
| `flask-smorest`, `apiflask`, `spectree`, `flask-pydantic` | marshmallow / pydantic under a Flask decorator that also **generates** the OpenAPI document — the path [openapi-plan](openapi-plan.md) decision 4 rejects: the routes are design, written before the code, and the generated error bodies are the library's. |

## Scorecard

✓ meets the rule · ≈ meets it with an adapter · ✗ cannot, or contradicts it

| | R3 unknown keys as data | R4 strict types, `19.0` int | R5 finite | R6 `null` distinct | E1 codes | E2 path + index | E3 first error, our order | S1 DTOs stay the one source | S2 no new dependency |
|---|---|---|---|---|---|---|---|---|---|
| hand-written layer (today) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| marshmallow | ✓ | ≈ custom field | ✓ | ≈ by message | ≈ by message | ✓ | ≈ sort + pick | ✗ (≈ with marshmallow-dataclass) | ✗ |
| pydantic v2 | ✓ | ≈ custom validators | ✓ | ≈ by input | ✓ map | ✓ | ≈ sort + pick | ✓ `TypeAdapter` | ✗ compiled |
| jsonschema | ≈ parse message | ✓ | ✗ post-check | ✗ post-check | ✓ map | ✓ | ≈ undocumented order | ✓ via the YAML | ≈ present, undeclared |
| protobuf (measured) | ≈ first key, in message; camelCase also accepted | ✗ strings and `true` coerced; `19.0` ✓ | ≈ parsed NaN ✓, `"NaN"` ✗, big int → `OverflowError` | ✗ null = unset | ✗ message prefixes | ≈ parse message | ✓ | ✗ `.proto` | ✗ + `protoc` |
| msgspec | ✗ own check | ✗ | ✗ | ≈ | ✗ parse message | ≈ parse message | ✓ | ✓ | ✗ |

## Decision

1. **The request path keeps the hand-written layer.** Every row of the yardstick is met today,
   byte-for-byte against the contract's examples, with no dependency; every library needs an
   adapter of comparable size to meet R4–R6 and E1–E3, and adds the dependency on top. The
   contract's own line — "the shape layer exists precisely so that no `TypeError` from the
   model ever surfaces" — is satisfied by about 440 lines (docstrings included) we own and can read.
2. **`jsonschema` is used in tests**, against `backend/openapi.yaml`, to keep the document
   honest ([openapi-plan](openapi-plan.md), drift guards 5–7). It is declared in
   `requirements-dev.txt`, not `requirements.txt`.
3. **Protobuf is used as the declaration of the fields, without gRPC** (decided 2026-11-03,
   after the two experiments). The measurement above stands: proto3's JSON mapping cannot
   validate the request path (strings and `true` are numbers, `null` is the default, no
   `required`, camelCase aliases; 12 of the 24 refusals, 11 for the contract's reason, and
   `10**400` crashes with `OverflowError`), so `ParseDict` does **not** replace the shape layer.
   What protobuf does is declare the schema: [`experiments/protobuf-swagger/`](experiments/protobuf-swagger/)
   generates the OpenAPI `SimulationInput` from an annotated `.proto` and the result agrees with
   `FIELD_SPECS` and the layer on 11 of 11 bodies. **Open:** the `.proto` is then a second
   declaration next to the DTOs (decision `field-specs-from-dtos`); either a drift test keeps
   them equal (it caught five wrong defaults on its first run) or the DTOs are generated from
   the `.proto`. To be settled before the schema task starts.
4. **Revisit** if one of these happens: the DTOs gain fields faster than the layer's one-line
   `UPPER_BOUNDS`/`UNITS` entries keep up; pydantic enters the project for another reason;
   or the contract drops E3 (first error in a fixed order) in favour of "all errors at once",
   at which point marshmallow's or pydantic's native error dict becomes the better fit and the
   adapter shrinks to a code map.

## What would change the answer

The contract's error section is the deciding factor, not the type rules. If the front-end
asks for **all** field errors in one response (to highlight every bad field at once), E3 flips
from "first in our order" to "all, grouped by field" — which is what marshmallow and pydantic
do natively. That is a contract revision (the `400` body would gain an `errors[]` array), and
this evaluation should be re-run against it.

## Appendix: the protobuf experiment, verbatim

`docs/experiments/protobuf-validation/` holds `simulation_input.proto`, the generated
`simulation_input_pb2.py` and `experiment.py`; the docstring of the script has the four
commands to reproduce. Output of the run recorded here (protobuf 7.36.2, Python 3.12):

```
=== POST /api/simulations — proto3 JSON mapping vs the contract vs the layer ===

# body is an array
  contract : 400 wrong_type body
  protobuf : ParseError: Failed to parse 1 field: expected string or bytes-like object, got 'int'.
  layer    : 400 wrong_type body

# string for a number
  contract : 400 wrong_type list_price
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : 400 wrong_type list_price

# boolean for a number
  contract : 400 wrong_type list_price
  protobuf : accepted -> {"list_price": 1.0, "months_remaining": 19}
  layer    : 400 wrong_type list_price

# 19.0 for an integer
  contract : accepted (months_remaining = 19)
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : accepted -> months=19 list_price=440000.0 dp%=20.0

# 19.5 for an integer
  contract : 400 wrong_type months_remaining
  protobuf : ParseError: Couldn't parse integer: 19.5 at SimulationInput.months_remaining
  layer    : 400 wrong_type months_remaining

# "19" for an integer
  contract : 400 wrong_type months_remaining
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : 400 wrong_type months_remaining

# true for an integer
  contract : 400 wrong_type months_remaining
  protobuf : ParseError: Bool value True is not acceptable for integer field at SimulationInput.months_remaining
  layer    : 400 wrong_type months_remaining

# two unknown fields
  contract : 400 unknown_field fgts_upfrnt (message lists both)
  protobuf : ParseError: Message type "sincero.SimulationInput" has no field named "fgts_upfrnt" at "SimulationInput".
 Available Fields(except extensions): "['name', 'listPrice', 'monthsRemaining', 'downPaymentPct', 'fgtsUpfront', 'cashUpfront', 'developerInstallment', 'balloonMonths', 'inccRatePa', 'bankRatePa', 'termMonths', 'itbiPct', 'registryPct', 'incomeCommitmentRatio', 'preApprovedCredit', 'proSolutoMonths']"
  layer    : 400 unknown_field fgts_upfrnt

# missing months_remaining
  contract : 400 missing_field months_remaining
  protobuf : accepted -> {"list_price": 440000.0}
  layer    : 400 missing_field months_remaining

# null on itbi_pct
  contract : 400 null_not_allowed itbi_pct
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : 400 null_not_allowed itbi_pct

# null on developer_installment
  contract : accepted (absent)
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : accepted -> months=19 list_price=440000.0 dp%=20.0

# NaN (parsed float)
  contract : 400 not_finite list_price
  protobuf : ParseError: Couldn't parse NaN, use quoted "NaN" instead at SimulationInput.list_price
  layer    : 400 not_finite list_price

# "NaN" (string)
  contract : 400 wrong_type list_price
  protobuf : accepted -> {"list_price": NaN, "months_remaining": 19}
  layer    : 400 wrong_type list_price

# Infinity
  contract : 400 not_finite list_price
  protobuf : ParseError: Couldn't parse Infinity or value too large, use quoted "Infinity" instead at SimulationInput.list_price
  layer    : 400 not_finite list_price

# months_remaining 5000
  contract : 400 out_of_range months_remaining
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 5000}
  layer    : 400 out_of_range months_remaining

# list_price 10**400
  contract : 400 not_finite list_price
  protobuf : OverflowError: int too large to convert to float
  layer    : 400 not_finite list_price

# months_remaining 2**31
  contract : 400 out_of_range months_remaining
  protobuf : ParseError: Failed to parse months_remaining field: Value out of range: 2147483648.
  layer    : 400 out_of_range months_remaining

# balloon item 6.5
  contract : 400 wrong_type balloon_months[1]
  protobuf : ParseError: Failed to parse balloon_months field: Couldn't parse integer: 6.5 at SimulationInput.balloon_months[1].
  layer    : 400 wrong_type balloon_months[1]

# balloon item "12"
  contract : 400 wrong_type balloon_months[1]
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19, "balloon_months": [6, 12]}
  layer    : 400 wrong_type balloon_months[1]

# balloon item null
  contract : 400 null_not_allowed balloon_months[1]
  protobuf : ParseError: Failed to parse balloon_months field: null is not allowed to be used as an element in a repeated field at SimulationInput.balloon_months[1].
  layer    : 400 null_not_allowed balloon_months[1]

# 61 balloon months
  contract : 400 out_of_range balloon_months
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19, "balloon_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]}
  layer    : 400 out_of_range balloon_months

# omitted defaults
  contract : accepted; down_payment_pct resolves to 20.0
  protobuf : accepted -> {"list_price": 440000.0, "months_remaining": 19}
  layer    : accepted -> months=19 list_price=440000.0 dp%=20.0

# the RA example
  contract : accepted
  protobuf : accepted -> {"name": "RA", "list_price": 440000.0, "months_remaining": 19, "fgts_upfront": 13000.0, "developer_installment": 2500.0, "balloon_months": [6, 12]}
  layer    : accepted -> months=19 list_price=440000.0 dp%=20.0

=== POST /api/comparisons (nested: base + candidates) ===

# candidate[1] months is a string
  contract : 400 wrong_type candidates[1].months_remaining, index 1  (accepted by proto3: strings are numbers)
  protobuf : accepted -> {"base": {"fgts_upfront": 13000.0}, "candidates": [{"list_price": 440000.0, "months_remaining": 19}, {"list_price": 396000.0, "months_remaining": 19}]}

# candidate[1] has an unknown key
  contract : 400 unknown_field candidates[1].foo, index 1
  protobuf : ParseError: Failed to parse candidates field: Message type "sincero.SimulationInput" has no field named "foo" at "ComparisonRequest.candidates[1]".
 Available Fields(except extensions): "['name', 'lis

# candidate[1] months 19.5
  contract : 400 wrong_type candidates[1].months_remaining, index 1
  protobuf : ParseError: Failed to parse candidates field: Couldn't parse integer: 19.5 at ComparisonRequest.candidates[1].months_remaining.

# candidates is an object
  contract : 400 wrong_type candidates
  protobuf : ParseError: Failed to parse candidates field: repeated field candidates must be in [] which is {'list_price': 1} at ComparisonRequest.

# candidates is empty
  contract : 400 out_of_range candidates
  protobuf : accepted -> {}

=== timing, the RA body, mean of 5000 runs ===
  protobuf ParseDict :   33.8 us
  layer              :   26.0 us
```
