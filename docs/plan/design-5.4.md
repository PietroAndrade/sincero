# Design: 5.4, `service Simulations` and revision 7 of the contract

Status: design, 2026-11-04, for branch `feat/service-definition`. Task: [tasks.md](../../tasks.md)
5.4 (backlog item 2, Enabler, 5 pts, depends on 5.3c, which is merged). Decisions it applies:
[api-protocol-and-language](../decisions/api-protocol-and-language.md) (Connect, typed results with a
`FieldMask`, `invalid_argument` + `ErrorInfo`) and
[required-fields-explicit-presence](../decisions/required-fields-explicit-presence.md).

## Goal

The API has one written definition: `backend/proto/sincero/simulations.proto` declares
`service Simulations` with one RPC per route of revision 6, and `docs/api-contract.md` revision 7
says which RPC replaces each route and which Connect code replaces each error `code`. Nothing is
served yet (5.6) and no rule is enforced yet (5.5). This task fixes the **shape** that 5.5 to 5.12
fill in, so it is the last cheap moment to change it.

Who benefits: the next tasks (5.5 to 5.12) and the front-end (M6) read one contract instead of
three statements of it. No buyer sees anything yet.

## Acceptance

- **AC1.** Given the `.proto`, When `protoc` compiles it, Then it compiles and the service has the
  RPCs of the [table below](#2-the-rpcs), no more, no fewer.
- **AC2.** Given the RPCs, When their options are read, Then exactly the reads carry
  `NO_SIDE_EFFECTS`.
- **AC3.** Given `make proto` on a clean tree, When it finishes, Then `git diff` is empty.
- **AC4.** Given the ten routes of revision 6, When revision 7 is read, Then each names an RPC that
  exists in the compiled service.
- **AC5.** Given the fourteen `code`s of the revision 6 error table, When revision 7 is read, Then
  each names a Connect code and, for `invalid_argument`, the detail type.

## Out of scope

- `buf.validate` rules other than the two from 5.3c, the CEL rule, unknown-field refusal (5.5).
- Any server code, the `connectrpc` app, interceptors, `make api` (5.6), the store (5.7), the RPC
  bodies (5.8 to 5.12).
- The typed sections of the result (`down_payment`, `mortgage`, …). They are written with their
  mirror test in 5.8, as the decision says. See [section 3](#3-messages).
- Retiring `api_requests.py` and `openapi.yaml` (5.13). `buf lint` and `buf breaking` (no `buf` CLI
  in the repo yet; revisit with 5.5).
- The experiments under `docs/experiments/`: left as they are, as evidence.

## Today

| Piece | State |
|---|---|
| `simulation_input.proto` | `SimulationInput`, and already `ComparisonRequest`, `WhatIfRequest`, `CashLadderRequest` ("declared so the four POST bodies share one schema") |
| `docs/experiments/protobuf-languages/connect/proto/sincero/api.proto` | a draft service of 8 RPCs; `GetNode` returns JSON bytes; `Summary` has 3 columns |
| `docs/api-contract.md` | revision 6, REST; says revision 7 will restate it as RPCs |
| Generation | `tools/gen_dto.py` (DTO fields) and the experiment's `generate.sh`; no `make proto` |
| Plugins | `connectrpc`, `protoc-gen-py`, `protoc-gen-connectrpc` installed in `.venv` by hand, not in `requirements-dev.txt`; `protoc-gen-es` only in the experiment's `node_modules` |

## Design

### 1. The file

**`backend/proto/sincero/simulations.proto`**, package `sincero`, importing `simulation_input.proto`.
The experiment's draft is called `api.proto`; the real file gets another name because the
experiment's `generate.sh` puts its own `proto/` first on the include path and `protoc` would
silently pick the draft over the real file.

The existing `ComparisonRequest`, `WhatIfRequest` and `CashLadderRequest` move out of
`simulation_input.proto` into this file, renamed to the request of their RPC (see below).
`simulation_input.proto` keeps only what `make dto` reads, which was always its job.

### 2. The RPCs

Revision 6 has ten rows; the decision's typed result removes the need for a node path, so two
rows share an RPC and two share another.

| Revision 6 route | RPC | Request | Response | Reads |
|---|---|---|---|---|
| `GET /api/fields` | `ListFields` | `ListFieldsRequest` | `ListFieldsResponse` | `NO_SIDE_EFFECTS` |
| `POST /api/simulations` | `CreateSimulation` | `CreateSimulationRequest` | `CreateSimulationResponse` | |
| `GET /api/simulations/{id}` | `GetSimulation` | `GetSimulationRequest` | `Simulation` | `NO_SIDE_EFFECTS` |
| `GET /api/simulations/{id}/result` | `GetResult` (no mask) | `GetResultRequest` | `SimulationResult` | `NO_SIDE_EFFECTS` |
| `GET /api/simulations/{id}/{path}` | `GetResult` (mask `path`) | same | same | same |
| `GET /api/comparisons?ids=…` | `GetComparison` | `GetComparisonRequest` | `Comparison` | `NO_SIDE_EFFECTS` |
| `GET /api/comparisons?ids=…&relative_to=…` | `GetComparison` (`relative_to` set) | same | same | same |
| `POST /api/comparisons` | `CreateComparison` | `CreateComparisonRequest` | `Comparison` | |
| `POST /api/simulations/{id}/what-if` | `CreateWhatIf` | `CreateWhatIfRequest` | `Comparison` | |
| `POST /api/simulations/{id}/cash-ladder` | `CreateCashLadder` | `CreateCashLadderRequest` | `Comparison` | |

Eight RPCs. Every RPC has its own request and response message (the experiment reused
`SimulationInput` as a request and `Comparison` is shared by four responses, which is allowed
for a response but not for a request; the lint rule is the reason to keep them separate and the
wire is the same). The URL stays `/sincero.Simulations/<Rpc>`; the reads are plain HTTP `GET`s.

`CreateSimulationRequest` wraps the input (`SimulationInput input = 1`) instead of being the input.
The JSON body is `{"input": {…}}`, one level deeper than revision 6's flat body. That is the price of
a request that can grow (an idempotency key, a label) without breaking clients; the CLI and the
gateway flatten it themselves.

### 3. Messages

| Message | Content |
|---|---|
| `Simulation` | `id`, `input` (the **resolved** input: every field set, defaults applied), `summary` |
| `Summary` | the 22 columns of the revision 6 summary table, typed (`name`, `list_price`, …, `peak_total`), plus `id`. No `href` (there are no routes) |
| `SummaryDelta` | the numeric columns of `Summary`, same names, same order |
| `ComparisonRow` | `summary`, and when the comparison has a reference: `overrides` (`SimulationOverrides`) and `delta` (`SummaryDelta`) |
| `Comparison` | `rows`, and `relative_to` (a `Summary`) when a reference was asked for |
| `SimulationResult` | **placeholder in 5.4**: an empty message with a comment naming 5.8. The ten sections are added there, with the test that builds the typed result and `simulation_to_dict` from the same simulation |
| `GetResultRequest` | `id`, `google.protobuf.FieldMask mask` (paths like `financing.sac`, as the revision 6 URL path) |
| `GetComparisonRequest` | `repeated string ids`, `optional string relative_to`, `FieldMask columns` (the old `?fields=`) |
| `ListFieldsResponse` | `repeated FieldSpec`: `name`, `group`, `type`, `unit`, `default`, `nullable`, `required`. Today `api_requests.py` builds this from the DTOs; the `.proto` already holds name, group, default and nullability, so 5.9 can build it from the descriptor and the units stay in `api_requests.UNITS` until then |

An empty `SimulationResult` is honest about being unfinished and keeps 5.4 from copying
`simulation_to_dict` field by field without its test. The cost is that `GetResult` returns nothing
useful until 5.8 and the generated clients change then. Nothing consumes them before that.

### 4. A finding: partial inputs and the required fields

5.3c made `list_price` and `months_remaining` `required` on `SimulationInput`, and `protovalidate`
checks nested messages. Two bodies of the contract carry **partial** inputs on purpose:

- `base` of a comparison: `{"fgts_upfront": 13000}` is valid; the candidates supply the rest (the
  contract's own example).
- `variations` of a what-if: `{"incc_rate_pa": 4.0}`, which override a stored simulation.

Typed as `SimulationInput`, both would be refused for a missing `list_price`, and 5.5 would find out
when it enforces the rules.

**Decision: add `SimulationOverrides`**, the same sixteen fields, all with explicit presence, no
rules, used for `base`, `candidates` (a candidate is `{**base, **candidate}` and has no
requirements of its own; the merged input is validated, which is the model's `422`, item by item)
and `variations`. A test pins that its field names, numbers and types equal `SimulationInput`'s, so
the two cannot drift. It is hand-written: generating a second message from the first is not worth a
generator for 16 lines, and the test is the guard.

Two details:

- `balloon_months` is `repeated` and has no presence, so an override cannot say "clear the balloons"
  (revision 6: `{"balloon_months": []}`). In `SimulationOverrides` it is
  `optional BalloonMonths balloon_months`, with `message BalloonMonths { repeated int32 months = 1; }`.
- `name` stays a plain string there too.

### 5. Revision 7 of `api-contract.md`

A new section **"Revision 7: the RPCs"** at the top, before "The flow". The old sections stay: they are
the source of the business semantics, and the status paragraph already says so. The new section holds:

1. The table of [section 2](#2-the-rpcs).
2. **The error table**, one row per revision 6 `code`:

| Revision 6 `code` (status) | Connect code | Detail |
|---|---|---|
| `malformed_json` (400) | `invalid_argument` | none; the message says the body is not valid JSON |
| `wrong_type` (400) | `invalid_argument` | `BadRequest` violation on the field |
| `unknown_field` (400) | `invalid_argument` | `BadRequest` violation; needs the codec set to refuse (5.5) |
| `missing_field` (400) | `invalid_argument` | `BadRequest` violation, rule `required` |
| `null_not_allowed` (400) | none: **accepted** | see the behaviour changes |
| `not_finite` (400) | `invalid_argument` | `BadRequest` violation, rule `double.finite` |
| `out_of_range` (400) | `invalid_argument` | `BadRequest` violation, the rule's id (`double.lte`, `int32.gte_lte`, `repeated.max_items`) |
| `invalid_value` (400) | `invalid_argument` | `BadRequest` violation, the rule's id |
| `not_found` (404), unknown id | `not_found` | `ErrorInfo` reason `simulation_not_found`, metadata `id` |
| `not_found` (404), unknown route | `unimplemented` | none; the protocol answers it |
| `not_found` (404), a `path` that is not a node | `invalid_argument` | `BadRequest` violation on `mask` |
| `method_not_allowed` (405) | none | the Connect protocol answers; no RPC is reachable by the wrong verb |
| `payload_too_large` (413) | `resource_exhausted` | none |
| `unsupported_media_type` (415) | none | the Connect protocol answers (HTTP 415) |
| `invalid_input` (422) | `invalid_argument` | `ErrorInfo` reason `invalid_input`, message verbatim |
| `internal_error` (500) | `internal` | constant message; the id is in the `X-Request-Id` header and in `ErrorInfo` metadata `request_id` |

3. **Behaviour changes** the move to proto3 JSON and `protovalidate` causes, none silent:
   - `null` for a field with a default (`"itbi_pct": null`) is no longer refused: proto3 JSON reads it
     as "absent", and the default applies. Revision 6 refused it (`null_not_allowed`). `null` for
     `list_price` or `months_remaining` is still refused, as `required`
     (decision, variant D).
   - Violations come back **all at once** in `BadRequest`, not "the first in a fixed order". The
     "order of checks" list stops being contractual, except that the model's `invalid_input` is only
     reached when no rule of the `.proto` is violated.
   - Numbers sent as strings (`"440000"`) and camelCase keys are accepted by proto3 JSON.
   - `href`, `Location` and the `sections` map of `GET /api/simulations/{id}` are gone: there are no
     routes, and the typed `Simulation` and `FieldMask` paths replace the map.
   - The `201`/`200` split does not exist; `CreateSimulation` answers with the id whether or not it
     already existed (revision 6 already said so).
4. A line at the top of each old section: "Business semantics; the wording of routes and status codes
   is superseded by revision 7".

### 6. `make proto`

One target, run from `backend/`:

```
make proto
```

runs `grpc_tools.protoc` (the one `make dto` uses) once over `simulation_input.proto` and
`simulations.proto` with `--descriptor_set_in=proto/buf_validate.binpb` and three plugins:

| Output | Plugin | Directory |
|---|---|---|
| Python messages | `protoc-gen-py` (pip) | `backend/app/api/gen/` |
| Python service | `protoc-gen-connectrpc` (pip) | same |
| TypeScript messages and service | `protoc-gen-es` (npm) | `frontend/src/gen/` |

The Python output goes inside the `app` package on purpose: the generated modules import each other
and `buf/validate` relatively (`from ..buf.validate import validate_pb`; the experiment hit
"attempted relative import beyond top-level package" when `gen/` was a path root). `app/models` must
not import it (5.6 asserts that).

The generated files are committed, as `input_fields.py` is. Versions are pinned so that "no diff" is
reproducible: `connectrpc`, `protoc-gen-py`, `protoc-gen-connectrpc`, `protobuf-py` in
`requirements-dev.txt` (the first and last move to `requirements.txt` with 5.6), and
`@bufbuild/protoc-gen-es`, `@bufbuild/protobuf`, `@bufbuild/protovalidate` in a new
`frontend/package.json` with a lockfile.

`make proto-check` runs the same into a temporary directory and diffs. The Python half is also a
pytest (`tests/test_proto_generated.py`, like `test_generated_module_is_up_to_date`) that skips when
a plugin is missing; the TypeScript half needs `node` and runs only in `make proto-check`.

## Tests

New, in `backend/tests/test_service_definition.py`, on the compiled descriptor:

1. The service is `sincero.Simulations` and its RPC names are exactly the eight of the table.
2. The reads (`ListFields`, `GetSimulation`, `GetResult`, `GetComparison`) are `NO_SIDE_EFFECTS` and
   the four writes are not. A new RPC without a declared level fails the test (the default level is
   `IDEMPOTENCY_UNKNOWN`, which is not accepted).
3. Every RPC has a request and a response message of its own name (`<Rpc>Request`; the response is
   named in the table) and no request type is shared.
4. `SimulationOverrides` has the field names, numbers and scalar types of `SimulationInput`, each
   with explicit presence, and no `buf.validate` rule.
5. `SimulationInput` has not changed: `make dto` still leaves no diff (existing test).

New, in `backend/tests/test_contract_revision.py`, on `docs/api-contract.md`:

6. Revision 7's RPC table lists exactly the ten routes of revision 6 (the route column is compared
   with the list in the document's own "Routes" table), and every RPC it names exists in the service.
7. Every `code` in the revision 6 error table appears in revision 7's error table with a Connect
   code, and every Connect code it uses is one of the sixteen of the protocol.
8. Every `invalid_argument` row names a detail type (`BadRequest` or `ErrorInfo`) or says `none`.

`test_proto_generated.py` (Python half of `make proto`) as in section 6.

## Docs to update in the same PR

- `docs/api-contract.md`: revision 7 section; status paragraph; the one-line note on old sections.
- `docs/decisions/api-protocol-and-language.md`: the "What changes in the contract" table points to
  revision 7 as done; question 1's "task 5.8" is unchanged.
- `backend/README.md` (layout: `app/api/gen/`, `make proto`, `proto/simulations.proto`) and the root
  `CLAUDE.md` command list (`make proto`).
- `ROADMAP.md` if it names `api.proto`.
- `tasks.md` 5.4 checked, with the date and test count (untracked, local).

## Order of work

1. Pin and install the plugins; add `frontend/package.json`; make `make proto` run on the existing
   `simulation_input.proto` alone and generate it (no service yet). `make test` still passes.
2. Write `simulations.proto` with the eight RPCs and the messages of [section 3](#3-messages); move
   the three request messages; tests 1 to 5. Run `make dto` (no diff) and `make proto`.
3. Revision 7 of the contract; tests 6 to 8.
4. `make proto-check`, the READMEs, `CLAUDE.md`.

Commit by concern, one per step.

## Definition of done (from tasks.md, with the checks)

| Criterion | Check |
|---|---|
| The `.proto` compiles | `make proto` runs; tests 1 to 3 |
| `make proto` leaves no diff | `make proto && git diff --exit-code backend/app/api/gen frontend/src/gen` |
| One RPC per row, reads `NO_SIDE_EFFECTS` | tests 1, 2 and 6 |
| Revision 7 has no row of revision 6 without an RPC | test 6 |
| Each error `code` has a Connect code, `BadRequest` in the details | tests 7 and 8 |
| `make test` green | existing 238 pytest and 54 scenarios, plus the new tests |

## Decisions for you

**Answered 2026-11-05: all four accepted as recommended** (1 `SimulationOverrides` hand-written with a
drift test; 2 TypeScript in `frontend/src/gen/`; 3 `CreateSimulationRequest` wraps the input;
4 `SimulationResult` is a placeholder until 5.8).

1. **`SimulationOverrides` (section 4).** Recommended: a second, hand-written message with a drift
   test. Alternatives: `SimulationInput` for everything and move the `required` rule to a CEL
   rule on the RPC requests that need it (it hides the rule from the generated TypeScript type and
   undoes part of 5.3c); or split `base`/`variations` into a map of field name to value (loses
   types). Needs your answer before step 2.
2. **Where the TypeScript client is generated.** Recommended: `frontend/src/gen/`, creating
   `frontend/` with only `package.json` and the lockfile now, because M6 builds there and the move
   would otherwise touch every import. Alternative: `backend/gen/ts/` now, moved in M6.
3. **`CreateSimulationRequest` wraps the input** (section 2). Recommended. Alternative: the request
   is `SimulationInput` itself, as in the experiment: a flat JSON body like revision 6 and no extra
   level, but a request that cannot grow.
4. **`SimulationResult` as a placeholder** (section 3). Recommended: keeps 5.4 at 5 points and the
   mirror test in one place. Alternative: write the ten sections now (about 8 pts) and 5.8 shrinks
   by the same amount.

## Risks

| Risk | Mitigation |
|---|---|
| "No diff" is not reproducible: a plugin version changes its output | Pin all versions (section 6); `make proto-check` in the PR |
| The generated Python imports break (`..buf`), as in the experiment | Output inside the `app` package; step 1 proves it on the existing file before the service exists |
| `protoc` picks the experiment's `api.proto` over the real file | The real file is `simulations.proto` |
| Moving three messages out of `simulation_input.proto` changes its generated descriptor and breaks the experiments' pinned counts | `simulation_input.pb` is only read by `gen_dto` (`SimulationInput`), and the experiments build their own copy; run `pytest docs/experiments/protobuf-languages/python` and `npm test` once, as 5.3c did |
| The `frontend/` directory starts the front-end by accident | It holds a `package.json`, a lockfile and `src/gen/`, with a README line saying so |
| `null` accepted for defaulted fields (behaviour change) goes unnoticed | It is listed in revision 7 and pinned by a test in 5.5 |
| `GetResult` returns an empty message until 5.8 | Nothing serves it before 5.6; the placeholder says so in the `.proto` |
