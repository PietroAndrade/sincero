# Decision: the API is a protobuf service (Connect RPC); the backend stays Python, the front-end is TypeScript

*Status: accepted, 2026-11-03. Evidence:
[`../protobuf-languages.md`](../protobuf-languages.md) (the language comparison) and
[`../experiments/protobuf-languages/connect/`](../experiments/protobuf-languages/connect/) (a
TypeScript client on a Python Connect server, run end to end, the real model behind it).
Supersedes the REST shape of [`../api-contract.md`](../api-contract.md) revision 6 and the
OpenAPI experiment in [`../experiments/openapi/`](../experiments/openapi/); the business rules,
the JSON payload of a simulation and the behave suite are untouched.*

## Context

Three things are wanted at once:

1. a **TypeScript front-end** (milestone 6), typed from the same schema the backend uses;
2. **API documentation** that is machine-readable and cannot drift from the implementation;
3. a **better way to validate the API contract** than a hand-written shape layer whose 400
   rules are re-stated in prose, in the layer, in its tests and in `openapi.yaml`.

Protobuf is the chosen schema language — `backend/proto/sincero/simulation_input.proto` is
already the source of truth for the input fields — and a rewrite of the backend is acceptable
because the business rules live in the `.feature` files, which any implementation has to pass.

The open question was the protocol and, with it, the backend language: **gRPC from Python, or a
TypeScript backend?** The earlier comparison ([`../protobuf-languages.md`](../protobuf-languages.md))
had answered the data-schema half — in both languages the generated code is usable, proto3's
gaps are the same, the proto3 JSON mapping is the same — but it had assumed Python had no
first-class RPC story for browsers. That assumption was wrong and is corrected here.

## What was established

- **Browsers do not speak gRPC.** Native gRPC needs HTTP/2 trailers, which `fetch` cannot read.
  A browser client uses **gRPC-Web** or the **Connect protocol** (Connect: plain HTTP/1.1 or 2,
  JSON or binary, unary calls as ordinary `POST`s — or `GET`s when the RPC is marked
  `idempotency_level = NO_SIDE_EFFECTS`; `curl`-able). The front-end library is
  `@connectrpc/connect-web` either way. So "gRPC for Python" really means "a server that
  speaks gRPC-Web or Connect to the browser".
- **Python has it natively now.** `connectrpc` (Connect for Python, official, 0.13, verified
  against the Connect conformance suite) serves **Connect, gRPC and gRPC-Web** from one
  WSGI/ASGI application — no Envoy, no `grpcwebproxy`. `grpcio` alone would need a proxy for
  the browser. The experiment ran a three-RPC service on uvicorn, with the existing `simulate`
  and JSON view behind it, and a generated TypeScript client called it over Connect+JSON,
  Connect+binary and gRPC-Web; same ids, the model's `SimulationError` text verbatim as
  `INVALID_ARGUMENT`, `NOT_FOUND` for an unknown id, a node read as an HTTP `GET`.
- **One `.proto`, one code generation, both sides.** `protoc` with three plugins —
  `protoc-gen-py` (messages, `protobuf-py`), `protoc-gen-connectrpc` (a typed service
  `Protocol`, an ASGI app, a client) and `protoc-gen-es` (messages and the service descriptor
  for TypeScript) — produced 2,189 lines for a draft of eight RPCs; the server implementation
  of three of them is 89 lines. All three plugins install from pip/npm; no Go, no BSR.
- **`protobuf-py` changes the Python DTO picture.** It generates readable, fully typed,
  slotted classes with `has_field`, `from_json`, `to_json` — not the opaque `_pb2` descriptor
  dumps. They are still mutable and unhashable, so the domain's frozen dataclasses stay; but
  the boundary code reads the descriptor instead of a generated table.
- **The proto3 JSON mapping becomes the contract's type rules**, in any language: strings are
  accepted for numbers, `null` is "unset", both `list_price` and `listPrice` are accepted.
  Two of the contract's rules survive by configuration: unknown keys are refused (the codec's
  `ignore_unknown_fields=False`; it defaults to `True`), and a fractional integer or a `null`
  inside a list is refused by the mapping itself. The rest of the hand-written shape layer goes
  away; the rules that are *business* rules move into the `.proto` as `buf.validate`
  constraints enforced by `protovalidate` (Python and TypeScript alike, verified).
- **Implicit presence is a real trap, not a theoretical one.** `months_remaining: 0` reached
  the model as "absent" (a `500`) until the conversion was written against the descriptor's
  presence information, because `to_json()` drops zero values of plain scalars. Required
  fields should either be converted field by field (as the experiment does) or be declared
  `optional` and checked with `protovalidate`'s `required`.

## The trade-off: Python + Connect vs a TypeScript backend

| | **Python backend, Connect** | **TypeScript backend, Connect** |
|---|---|---|
| What is rewritten | the API layer only (~the size of today's `api_requests.py`); the model (~1,500 lines), the views and the 54 behave scenarios with their steps stay | the model, the views, the step definitions and the support library; the `.feature` files carry over to Cucumber.js |
| Toolchain | `buf`/`protoc` + `protoc-gen-py` + `protoc-gen-connectrpc` (pip) for the server, `protoc-gen-es` (npm) for the client: two package managers, one generation | `buf` + `protoc-gen-es` for both sides: one package manager, one generated module shared by server and browser |
| Server runtime | `connectrpc` 0.13 on any ASGI server (uvicorn); young (2025), conformance-tested, API surface may still move; fallback: `grpcio` + `sonora`/Envoy for gRPC-Web | `@connectrpc/connect-node` 2.2 (with Fastify/Express/http2); mature, the reference Connect implementation after Go |
| Validation in the `.proto` | `protovalidate` 2.1 — run, identical results to TypeScript | `@bufbuild/protovalidate` 1.3 — run; a ready-made Connect interceptor exists |
| The DTOs | `protobuf-py` classes at the boundary; the domain keeps its frozen dataclasses (`tools/gen_dto.py` stays, or the domain is rebuilt on the messages) | the generated types are the DTOs (finding 1 of the comparison); no generator |
| Performance | ~3 ms to simulate, 35–60 µs to parse; irrelevant at this API's scale | ~10× faster parsing; the model would have to be re-timed |
| API documentation | the `.proto` is the reference; OpenAPI via `protoc-gen-connect-openapi` (Go binary; see below) — the same in both columns | same |
| Risk | `connectrpc` maturity; two languages in the repository | the rewrite itself: every figure in 54 scenarios reproduced to the cent in a second language; two implementations during the transition |
| What the `.feature` files buy | nothing needs re-proving: the scenarios already drive the model through the JSON view; only the gateway changes (`EngineGateway` → a gateway over the generated Python client) | the proof that the port is faithful — this is where they are indispensable |

What is **the same in both columns**, and therefore not a reason to choose: the `.proto` as the
single contract; Connect and gRPC-Web to the browser without a proxy; `protovalidate` rules in
the `.proto`; the proto3 JSON mapping as the type rules; the error model; the OpenAPI story.

## Decision

**Keep the backend in Python, serve the API with Connect (`connectrpc`), generate the front-end
client with `protoc-gen-es`.** Reasons, in order:

1. The thing a rewrite would pay for — "the generated code is the DTO" — is worth ~300 lines of
   Python ([comparison, finding 6](../protobuf-languages.md)). The thing a rewrite would risk —
   the arithmetic behind 54 scenarios — is the whole product. The `.feature` files make a port
   *verifiable*, not free.
2. Every benefit that motivated the question is obtained without the port: the front-end is
   typed from the `.proto`; the contract is the `.proto` plus `buf.validate` rules, enforced by
   the same library on both sides; the API layer shrinks to RPC handlers; the shape layer and
   its 92 tests are retired, not rewritten.
3. The one cost specific to this column — `connectrpc`'s youth — is bounded: the server is a
   standard ASGI app, the generated service is a `Protocol`, and `grpcio` (mature) with a
   gRPC-Web adapter is the fallback with the same `.proto`.

Revisit towards a TypeScript backend if a second reason appears (a team that only writes
TypeScript; a deployment that wants one runtime; the model growing a front-end-only twin for
"instant" what-ifs, which would be the moment to make TypeScript the one implementation).

## What changes in the contract

The *figures* and the payload of a simulation do not change; the *surface* does. Revision 7 of
`api-contract.md` records:

| Today (REST, revision 6) | With Connect |
|---|---|
| `POST /api/simulations`, `GET /api/simulations/{id}[/{path}]`, `GET`/`POST /api/comparisons`, `POST …/what-if`, `…/cash-ladder`, `GET /api/fields` | `service Simulations { CreateSimulation, GetSimulation, GetNode, GetComparison, CreateComparison, CreateWhatIf, CreateCashLadder, ListFields }` at `/sincero.Simulations/<Rpc>`; the reads are `NO_SIDE_EFFECTS` → HTTP `GET`, cacheable |
| `{path}` into the payload, `?fields=` | typed messages for the ten sections of the payload, one RPC returning the whole typed result, and a `google.protobuf.FieldMask` for the projection (question 1) |
| Shape rules 2–7, `400` with `code`/`field`/`index` | the proto3 JSON mapping (strings for numbers accepted; `null` = unset; camelCase accepted; unknown keys refused by configuration) + `buf.validate` rules; violations are Connect `invalid_argument` errors with `google.rpc.BadRequest` field violations in `details` |
| `422 invalid_input` with the model's message | `invalid_argument` with the same message and an `ErrorInfo` detail (question 2) |
| `404`, `405`, `413`, `415`, `500` bodies | Connect error codes (`not_found`, `unimplemented`, `resource_exhausted`, `internal`) with the protocol's JSON body `{code, message, details}`; HTTP statuses follow the protocol's mapping |
| `X-Request-Id`, `Location`, content-addressed ids, lifetime | ids and lifetime unchanged; request ids as an interceptor; `Location` has no equivalent (the response carries the id) |
| `openapi.yaml` hand-written + generated block | `protoc-gen-connect-openapi` generates OpenAPI 3.1 from the service, including `buf.validate` constraints as schema keywords — **not verified here** (a Go binary, GitHub-distributed; unreachable from the sandbox). Until verified, the `.proto` itself is the reference and `buf`'s generated docs are the human-readable form |
| `EngineGateway` / planned `HttpGateway` | a gateway over the generated `SimulationsClientSync`: the scenarios run unchanged over the wire |

## Rejected alternatives

| Alternative | Why not |
|---|---|
| `grpcio` only (native gRPC from Python) | the browser cannot call it; an Envoy/`grpcwebproxy` hop for every deployment, including tests |
| gRPC JSON transcoding (ASP.NET Core) for REST + Swagger from the `.proto` | the only tool that keeps the REST shape, but a third language and a rewrite; the REST shape is not what is wanted once the client is generated |
| Keep REST + the hand-written shape layer, generate only the front-end types from the `.proto` | what the comparison recommended as the zero-cost option; it keeps three statements of the contract (layer, prose, YAML) and a hand-typed client, which is what the question wants to retire |
| TypeScript backend now | see the trade-off: the same benefits, plus a rewrite whose only payoff is one language |

## Consequences

- `api_requests.py`, its tests and `openapi.yaml`'s hand-written half are retired when the
  service lands; `tools/gen_dto.py` stays until the domain is rebuilt on `protobuf-py`
  messages, if ever.
- The contract's type rules become the proto3 JSON mapping: a client that sends `"440000"` is
  accepted. The strict rules were protecting a hand-typed client; a generated one cannot send
  them.
- `buf.validate` rules in the `.proto` duplicate the model's validators until the validators
  are retired; the API ceilings (`≤ 600`) and the model's rules (`≥ 1`) then live in one place.
- New dependencies: `connectrpc`, `protobuf-py`, `protovalidate`, an ASGI server (runtime);
  `protoc-gen-py`, `protoc-gen-connectrpc` (dev). Flask and `flask-cors` go.
- Still to verify, outside this decision: `protoc-gen-connect-openapi` on a machine with GitHub
  access.

## The three open questions, answered

### 1. How the parts of a result are read: typed messages and a field mask

**Choice.** The ten sections of the payload (`simulation_to_dict`: `input`, `rates`,
`down_payment`, `mortgage`, `construction_interest`, `closing_costs`, `credit_gap`,
`total_cost`, `timeline` and the financing section) become typed messages. One RPC returns the
whole typed result, and a `google.protobuf.FieldMask` projects it.

**Reason.** The generic RPC of the experiment (`GetNode(id, path, fields)`) returns the node as
JSON bytes: in [`connect/output.txt`](../experiments/protobuf-languages/connect/output.txt)
(the `GetNode` call) the reply is `{"json":"eyJub21…"}`, base64 of untyped JSON. The TypeScript
client gets no type for any figure the charts of milestone 6 read, and removing that loss is
much of the reason for moving to protobuf. Typed messages cost more: they mirror
`simulation_to_dict` field by field and must change with it. They stay in step through a test
(task 5.8) that builds the typed result and the dict from the same simulation and compares them,
so the behave suite, which pins the dict, pins the messages too.

**Rejected.** The generic `GetNode` RPC returning JSON bytes: cheaper to write, but it moves the
payload's shape out of the `.proto`, back into prose and into hand-typed client code.

### 2. The Connect code of a failed model rule: `invalid_argument`

**Choice.** `invalid_argument` for both a rule of the `.proto` and a rule of the model. A detail
tells them apart: a `google.rpc.BadRequest` with the field violations when a `buf.validate` rule
fails, and an `ErrorInfo` with the reason `invalid_input` and the model's message when
`SimulationError` is raised. A client branches on the detail type: `BadRequest` marks a field,
`ErrorInfo` shows a message. `failed_precondition` is kept for a state the service does not have
yet.

**Reason.** Every model rule concerns only the values sent (`months_remaining >= 1`, FGTS plus
cash within the list price); none depends on the state of the system. `failed_precondition`
means "retry after the state is fixed", which is false here. The experiment already returns the
model's text verbatim as `invalid_argument`
([`connect/output.txt`](../experiments/protobuf-languages/connect/output.txt), lines 1-2, and
the `months_remaining 0` lines of the round trip).

**Rejected.** `failed_precondition` for the model's rules, to keep the `400`/`422` distinction as
two codes. The distinction survives as the detail type, without a code that promises a retry.

### 3. The "absent" trap: `optional` plus `required`

**Choice.** A required field is declared `optional` (explicit presence) and carries
`(buf.validate.field).required = true` next to its range rule. An absent field and an invalid one
are refused with different violations: `value is required` for the first, the range message for the
second. The first choice here was plain scalars with a rule that rejects zero. Comparing seven
variants showed it could not say "required" and could not protect a field whose zero is valid, so it
was replaced on 2026-11-04. The evidence and the full reasoning are in
[required-fields-explicit-presence](required-fields-explicit-presence.md).

**Reason.** In proto3 a plain scalar cannot tell zero from missing, and `to_json()` drops zero
values; that is how `months_remaining: 0` became a `500` in the experiment
([`connect/README.md`](../experiments/protobuf-languages/connect/README.md), lines 28-29).
`optional` alone is worse than nothing, since the rules of an unset field are skipped and an absent
field gets through; `required` closes that. The experiment's tests refuse an absent or zero
`list_price` and `months_remaining` before the model runs
([`test_experiment.py`](../experiments/protobuf-languages/python/test_experiment.py)).

| Required field (no default in [`simulation_input.proto`](../../backend/proto/sincero/simulation_input.proto)) | Declared as | Absent | Zero or out of range |
|---|---|---|---|
| `list_price` | `optional`, `required`, `double.gt = 0` | `value is required` | `must be greater than 0` |
| `months_remaining` | `optional`, `required`, `int32 = {gte: 1, lte: 600}` | `value is required` | the range message |
| `name` | unchanged, no rule | the empty string is the unnamed simulation and the service resolves it to `"CUSTOM"` ([contract](../api-contract.md), field table) | none |

`balloon_months` is `repeated`, not required: empty is its default. A new required field is declared
the same way, or is `optional` with a default.

**Rejected.** Plain scalars with a rule that rejects zero (the first choice), `optional` without
`required`, and converting field by field against the descriptor, for the reasons in the linked
decision.
