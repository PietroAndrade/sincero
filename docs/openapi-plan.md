# Plan: specifying the API in OpenAPI (YAML) and serving it with Swagger UI

*Status: proposed. Companion to [`api-contract.md`](api-contract.md) (revision 6), which stays
the normative document for everything a schema cannot say. Nothing here changes the contract.*

## Why

The contract is 1,300 lines of prose and tables — excellent for the *why*, poor for three jobs
that need the *what* in machine-readable form:

| Who | Needs | Today |
|---|---|---|
| The front-end (milestone 6, TypeScript) | types for every request and response body (`openapi-typescript`) | hand-typed from the tables |
| The Flask controller (milestone 5) and its tests | a way to prove the responses it sends are the ones documented | reading the markdown |
| Anyone trying the API | a page to click through the routes with the contract's examples pre-filled | `curl` |

One OpenAPI document gives all three, and Swagger UI renders it. The risk is the one this
project guards against everywhere: a **second source of truth**. The field table already
lives in the DTOs ([decision](decisions/field-specs-from-dtos.md)); the error codes live in
`api_requests.py`; the payload shape lives in `simulation_to_dict`. The plan below is mostly
about keeping the YAML from drifting from those.

## Decisions to take first

### 1. What is normative

**Recommendation:** the YAML is normative for *shapes* (routes, parameters, bodies, status
codes, response schemas, `code` enums, limits); the markdown is normative for *rules a schema
cannot express* and for the reasoning. Where they disagree, that is a bug in one of them, and a
test should have caught it (see [Drift guards](#drift-guards)).

What OpenAPI / JSON Schema **cannot** express, and therefore stays in prose (and in
`description` fields that quote it):

- the **order of checks** — "the client always sees the first broken rule in this order";
- **finiteness** — JSON has no `NaN`; the rule exists because Python's parser accepts it;
- `amounts` **strictly increasing**; `{}` is an invalid variation; `null` on a non-nullable
  field is `null_not_allowed` rather than a plain type error;
- the **content-addressed id** (same input → same id), lifetime and `expires_at` semantics;
- all-or-nothing creation; `index` only when the error is about one item;
- `overrides` as a diff of resolved inputs; `delta` arithmetic;
- the per-message `422` rules (they are the model's strings, already listed in the contract).

### 2. OpenAPI 3.1, not 3.0

3.1 aligns with JSON Schema 2020-12, which matters here in three concrete ways:

- `type: ["number", "null"]` for `developer_installment` / `pre_approved_credit` — exactly the
  contract's `number|null`, without 3.0's `nullable: true` workaround;
- `type: integer` accepts `19.0` and rejects `19.5` ("a mathematical integer"), which is the
  contract's rule 4 verbatim — the schema and `_check_integer` agree without a note;
- `examples` with names, so every example in the contract can be carried over with its caption
  (`string-for-a-number`, `fraction-of-a-month`, `unknown-field`…).

Swagger UI ≥ 5 renders 3.1. `openapi-spec-validator` validates it.

### 3. Where the file lives and who serves it

**Recommendation:** `backend/openapi.yaml`, one file, hand-written, checked in.

- The backend serves it at `GET /api/openapi.yaml` and Swagger UI at `GET /api/docs`; both are
  **outside** the contract (no `X-Request-Id` promises, no JSON error body — they are
  documentation, not the API) and excluded from the `HTTPException` → JSON handler's scope only
  in that sense; a `404` on `/api/docs/foo` is still JSON.
- Tests read it from `backend/tests/` by path; the front-end build reads
  `../backend/openapi.yaml` for type generation; Docker (milestone 7) copies it with the app.
- Alternative `docs/openapi.yaml`: closer to the prose, but the file is executable — served and
  tested by the backend — and `backend/` is where `make test` runs. Rejected, narrowly.
- One file, not `$ref`s across several: the document is ~900 lines, and a single file is what
  every tool (Swagger UI from a CDN, `openapi-typescript`, the validator) consumes without a
  bundling step.

### 4. Hand-written, generated, or verified?

| Option | Verdict |
|---|---|
| **A. Generate the whole YAML from code** (flask-smorest / apispec + marshmallow, or a custom emitter) | Rejected. The routes, status codes and error semantics are *design*, written before the code; generating them from decorators inverts that and drags in a dependency whose validation errors are not the contract's (`code`, `field`, `index`, fixed order). The libraries themselves — marshmallow, pydantic, jsonschema, protobuf, msgspec and the Flask wrappers — are evaluated against the contract's rules in [json-validation-tools.md](json-validation-tools.md). |
| **B. Hand-write everything** | Drifts silently on the next DTO field or error code. |
| **C. Hand-write the YAML; generate the one component that has a code source (`SimulationInput`) from `FieldSpec`** | Workable, but a generated block inside a hand-written file needs a marker-based rewrite and a "is it up to date" test anyway. |
| **D. Hand-write the YAML; tests assert it matches the code sources** | **Adopted.** The YAML stays one readable document; three small tests pin it to `FIELD_SPECS`, the error codes and the payload; a mismatch fails `make test` with a message naming the field. |

Generation (C) can be added later for `SimulationInput` if the DTOs change often; the tests
are the same either way.

The same question from the other side — could a validation library *consume* the YAML (or its
own schema) in the request path and replace `api_requests.py`? — is answered in
[json-validation-tools.md](json-validation-tools.md): no library meets the contract's error
rules (`not_finite`, `null_not_allowed`, first error in a fixed order) without an adapter the
size of the layer, so `jsonschema` is used in the drift guards below and nowhere else.

### 5. Swagger UI: no new runtime dependency

One static HTML page (`backend/app/static/docs.html`, ~20 lines) that loads `swagger-ui-dist`
from a pinned CDN URL and points at `/api/openapi.yaml`. `flask-swagger-ui` and friends add a
package for what is one `<script>` tag; Docker's nginx (milestone 7) can serve the same page
without the backend. Offline use is an open point (vendor the two dist files then).

## The document, section by section

### `info`, `servers`, `tags`

```yaml
openapi: 3.1.0
info:
  title: SINCERO API
  version: "0.6"            # = contract revision; bumped with the contract
  description: |
    Off-plan apartment cost simulator. A simulation is a resource … (three lines and a
    link to docs/api-contract.md for the rules a schema cannot state).
servers:
  - url: http://localhost:5000
tags: [simulations, fields, comparisons, what-ifs, cash-ladders]
```

### Operations — one per contract row, `operationId` = the verb the front-end will call

| Operation | `operationId` | Request body | 2xx | Errors (`code` values) |
|---|---|---|---|---|
| `GET /api/fields` | `listFields` | — | `200 FieldSpec[]` | — |
| `POST /api/simulations` | `createSimulation` | `SimulationInput` | `201 Created` + `Location` | `400` shape codes · `413` · `415` · `422 invalid_input` |
| `GET /api/simulations/{id}` | `getSimulation` | — | `200 SimulationResource` | `404 not_found` |
| `GET /api/simulations/{id}/result` | `getResult` | — | `200 SimulationPayload` | `404` |
| `GET /api/simulations/{id}/{path}` | `getNode` | — | `200` object or array (`?fields=`) | `400 invalid_value` · `404` |
| `GET /api/comparisons` | `getComparison` | — | `200 Comparison` (+ `relative_to`) | `400 missing_field/invalid_value/out_of_range/unknown_field` · `404` |
| `POST /api/comparisons` | `createComparison` | `ComparisonRequest` | `201` + `Location` | `400` (+`index`) · `413` · `415` · `422` (+`index`) |
| `POST /api/simulations/{id}/what-if` | `createWhatIf` | `WhatIfRequest` | `201` + `Location` | `400` (+`index`) · `404` · `413` · `415` · `422` (+`index`) |
| `POST /api/simulations/{id}/cash-ladder` | `createCashLadder` | `CashLadderRequest` | `201` + `Location` | same as what-if |

Every operation: `responses.default` → `Error` (covers `405`, `500`, and any code added
later); `X-Request-Id` declared once as a reusable response header and referenced from every
response.

The path walk is the one awkward route: `{path}` contains slashes (`financing/sac`), which
OpenAPI path templates do not allow. **Recommendation:** declare it as
`/api/simulations/{id}/{path}` with `path: {type: string, examples: [mortgage, financing/sac,
timeline/months]}` and a description that the slash is literal (Swagger UI will percent-encode
it; Flask decodes it; it works). The alternative — enumerating the ~25 known nodes as separate
paths — documents the section reference better but is noise in the UI and freezes a list the
contract says may grow. Deferred; the section reference becomes `SimulationPayload`'s schema
anyway (next point).

### `components.schemas`

| Schema | Source of truth | How the YAML says it |
|---|---|---|
| `SimulationInput` | `FIELD_SPECS` (the DTOs) | `type: object`, `additionalProperties: false`, `required: [list_price, months_remaining]`, one property per field with `type`, `default`, `maximum` / `maxItems` from the API limits, `description` = unit + meaning. `integer[]` → `{type: array, items: {type: integer}, maxItems: 60}` |
| `InputOverrides` | same | `SimulationInput` minus `required`, `minProperties: 1` — a candidate, a variation, or `base` |
| `FieldSpec` | `FieldSpec.to_dict()` | `name`, `group` (enum), `type` (enum of the five strings), `required`, `default`, `unit` |
| `ComparisonRequest` | contract | `base: InputOverrides` (optional), `candidates: {type: array, items: InputOverrides, minItems: 1, maxItems: 20}`, `additionalProperties: false` |
| `WhatIfRequest` | contract | `variations`, same bounds |
| `CashLadderRequest` | contract | `amounts: {type: array, items: {type: number, minimum: 0, maximum: 1e12}, minItems: 1, maxItems: 20}`; "strictly increasing" in the description |
| `Created` | contract | `{id, href}` |
| `SimulationResource` | contract | `id`, `href`, `created_at`, `expires_at` (`format: date-time`), `input: SimulationInput` (every field present, nullable ones possibly `null`), `summary: Summary`, `sections` |
| `Summary` | `summary_to_dict` | 21 properties, all `number` except `name`; `required` = all |
| `ComparisonRow` | contract | `allOf: [Summary]` + `id`, `href`; with a reference also `overrides: InputOverrides`, `delta` (Summary minus `name`) |
| `Comparison` | contract | `href`, `rows`, optional `relative_to: ComparisonRow` |
| `SimulationPayload` and its sections (`Rates`, `DownPayment`, `Mortgage`, `ConstructionInterest`, `ClosingCosts`, `Financing`, `AmortizationSchedule`, `CreditGap`, `TotalCost`, `Timeline`) | `simulation_to_dict` + the contract's section reference | one schema per section, rows as `items` schemas; `month` as `integer`; invariants (`len == months_remaining`) in descriptions |
| `Error` | the contract's error body | `required: [error, code]`; `code: {enum: [malformed_json, wrong_type, unknown_field, missing_field, null_not_allowed, not_finite, out_of_range, invalid_value, not_found, method_not_allowed, payload_too_large, unsupported_media_type, invalid_input, internal_error]}`; `field`, `index`, `request_id`; `additionalProperties: false` (the contract: "nothing else is ever in an error body") |

Per-status responses narrow the enum: the `400` response of `createSimulation` lists only the
seven shape codes; `422` only `invalid_input`; `500` only `internal_error`. Swagger UI shows
them per response, which is what a client branching on `code` wants to read.

### `examples`

Lifted verbatim from the contract, named, under each response — the `400` table alone is a
dozen. They are also **test fixtures**: see the drift guards. The RA input
(`{"name":"RA","list_price":440000,…,"balloon_months":[6,12]}`) is the request example
everywhere; the reference five are `createComparison`'s; `[0, 30000, 75000, 100000]` the ladder's.

## Drift guards (tests, `backend/tests/test_openapi.py`)

Each is a few lines; together they make the YAML as trustworthy as the code.

1. **It is valid OpenAPI 3.1** — `openapi-spec-validator` (dev dependency) on the file.
2. **`SimulationInput` ⇔ `FIELD_SPECS`.** For every spec: the property exists, its `type` is
   the spec's (`number|null` ⇔ `["number", "null"]`, `integer[]` ⇔ array of integer), its
   `default` is the spec's, `required` is exactly `REQUIRED_FIELDS`, `maximum` / `maxItems`
   equal `UPPER_BOUNDS` / `MAX_BALLOONS`, no extra property. The message names the field.
3. **`Error.code.enum` ⇔ the codes the code uses.** The shape layer's codes (grep'd from
   `api_requests.py` or exposed as a constant `CODES`) plus the Flask-side ones are exactly the
   enum, and each per-status response's enum is a subset.
4. **Every request example is accepted or rejected as documented.** Walk the YAML: each
   request example under a `2xx` goes through `simulation_input` / `comparison_inputs` /
   `what_if_inputs` / `cash_ladder_amounts` and succeeds; each example under a `400`/`422`
   response raises `ApiError` with that status and the example body's `code` / `field` /
   `index`. This is the test that turns the contract's examples into one parametrised check,
   and it needs no Flask.
5. **Every response example validates against its schema** — `jsonschema` (present as a
   transitive dependency today; to be declared in `requirements-dev.txt`, see
   [json-validation-tools.md](json-validation-tools.md)) with the 2020-12 validator; catches
   a renamed summary column or a missing `href`.
6. **`Summary` ⇔ `summary_to_dict`** and **`SimulationPayload` ⇔ `simulation_to_dict`**: the
   real RA payload validates against the schema, and every key of the payload is declared
   (`additionalProperties: false` on the section schemas makes the second half free).
7. Once the Flask controller exists: **every response of the test client validates against
   the schema of its status** — a fixture that wraps `client.open`, looks up
   `paths[route][method].responses[status]`, and validates. Optionally `schemathesis` against
   the test client for fuzzing; not required.

Guards 1–6 can be written **now**, against `api_requests.py` and the views, before the
controller exists. That is also the order to do it in.

## Steps

| # | Deliverable | Done when |
|---|---|---|
| 1 | `backend/openapi.yaml`: `info`, the nine operations with parameters and status codes, `Error`, `SimulationInput`, the three request schemas, `Created` — **no response payload schemas yet** | validator passes; guards 1–4 green; `make openapi` target runs the validator |
| 2 | Response schemas: `FieldSpec`, `Summary`, `ComparisonRow`, `Comparison`, `SimulationResource` | guards 5–6 green for those |
| 3 | `SimulationPayload` and the ten section schemas from the contract's section reference | the RA `simulation_to_dict` validates; `/result` and `{path}` responses documented |
| 4 | Examples: every example of the contract, named, in place | guard 4 covers all of the contract's `400`/`422` tables |
| 5 | Swagger UI: `app/static/docs.html`, routes `GET /api/docs` and `GET /api/openapi.yaml` (with the Flask controller, milestone 5) | the page loads, "Try it out" on `createSimulation` with the RA example returns `201` |
| 6 | Front-end hook: `npm run api-types` → `openapi-typescript ../backend/openapi.yaml -o src/api/types.ts` (milestone 6) | the form's field list is typed from `FieldSpec`; `Summary` keys are typed |
| 7 | Docs: `docs/README.md` row, `api-contract.md` header pointing at the YAML as the shape-normative companion, `backend/README.md` layout | — |
| 8 | Guard 7 when the controller lands; decide on `schemathesis` | — |

Steps 1–4 and 7 need nothing that does not exist today. Estimated size: the YAML ~900 lines,
the tests ~150.

## Open points

- **`{path}` with slashes** — template string (recommended) or enumerated nodes; see above.
- **`version`** — tie to the contract revision (`0.6`) or start semver at `1.0.0` when milestone 5
  ships. Recommendation: contract revision until then.
- **`GET /api/comparisons` `fields` and `relative_to`** — `fields` is a comma-separated string;
  document as `style: form, explode: false` array so Swagger UI offers a list, or as a plain
  string to match the wire exactly. Recommendation: plain string with a pattern; the array
  style misleads about `?fields=a&fields=b`, which the contract does not define.
- **Offline Swagger UI** — vendor `swagger-ui-bundle.js` + CSS (≈1.5 MB) or accept the CDN.
  Decide with Docker (milestone 7).
- **Help text** — `description` per input property duplicates `cli_controller.HELP`. The
  contract's open question (`field(metadata={"help": …})`) would give the CLI, `/api/fields` and
  the YAML one source; until then guard 2 checks types and defaults, not descriptions.
- **Generating `SimulationInput` (option C)** — revisit if the DTOs gain fields more than once
  a milestone.
