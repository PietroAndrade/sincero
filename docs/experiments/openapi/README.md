# Experiment: an OpenAPI document for the REST contract, with its input schemas generated from the `.proto`

*Status: tried, working, and not adopted. It describes revision 6 of
[`api-contract.md`](../../api-contract.md) and is kept as a record. The API is going to be a
protobuf service ([decision](../../decisions/api-protocol-and-language.md)), where the `.proto`
is the reference and an OpenAPI document of the REST routes has no job. Nothing in the
application, its `make` targets, `requirements-dev.txt` or the test suite uses these files.*

## What was done

`openapi.yaml` in this directory is the machine-readable form of the REST contract: OpenAPI
**3.1** (JSON Schema 2020-12), one file, no `$ref`s to other files, 1,377 lines. `gen_openapi.py`
generates the input schemas in it from `backend/proto/sincero/simulation_input.proto`.
`test_openapi.py` (154 tests) keeps the file honest against the code. They moved here from
`backend/openapi.yaml`, `backend/tools/gen_openapi.py` and `test_openapi.py`, with
the paths adjusted and nothing else changed; `make openapi`, the `pyyaml` and
`openapi-spec-validator` entries of `requirements-dev.txt` and the layout lines in
`backend/README.md` were dropped.

## Running it

From the repository root, in the backend's virtualenv with two extra packages:

```bash
cd backend
.venv/bin/pip install pyyaml openapi-spec-validator          # not in requirements-dev.txt
.venv/bin/python ../docs/experiments/openapi/gen_openapi.py --check       # exit 0: the generated block is current
.venv/bin/python ../docs/experiments/openapi/gen_openapi.py               # rewrite it after editing the .proto
.venv/bin/python -m pytest ../docs/experiments/openapi -p no:cacheprovider   # 154 passed
```

To read the document in a browser without a backend:

```bash
npx @redocly/cli preview-docs docs/experiments/openapi/openapi.yaml
docker run -p 8080:8080 -e SWAGGER_JSON=/s/openapi.yaml -v "$PWD/docs/experiments/openapi:/s" swaggerapi/swagger-ui
```

## Why it was not adopted

- A REST-shaped OpenAPI document needs a hand-written half (paths, responses, the `Error` body,
  examples) that no tool derives from a `.proto` without a `service`; only the input schemas
  were generated. That is two sources of truth plus tests to keep them equal.
- The language comparison ([protobuf-languages.md](../../protobuf-languages.md)) found that
  protoc plugins which do produce OpenAPI (`protoc-gen-openapi`, grpc-gateway's
  `protoc-gen-openapiv2`) need a `service` with HTTP annotations, are Go binaries, and follow
  proto3's JSON mapping, which contradicts the contract's strict types. The Go plugin that
  could do it for a Connect service was not verified.
- With the API as a protobuf service, the `.proto` itself is the contract and the front-end
  client is generated from it.

The rest of this file is the original description of the document, kept as written.

## Generated from the `.proto`, or hand-written?

The question was whether the document could be produced from
`backend/proto/sincero/simulation_input.proto`, which since
[input-fields-from-proto](../../decisions/input-fields-from-proto.md) is the source of truth for the
input fields. The answer is **partly**, and the split is exact:

| Part of the document | Source | Why |
|---|---|---|
| `components.schemas.InputFields`, `SimulationInput` — every input field with its type, nullability, default, description, owning group (`x-group`) | **generated** from the `.proto` by `gen_openapi.py`, between two marker comments | this is precisely what the `.proto` states; generating it is the same derivation that produces the DTOs |
| `maximum` / `maxItems` and `x-unit` on those fields | merged into the generated block from `app/controllers/api_requests.py` (`UPPER_BOUNDS`, `MAX_BALLOONS`, `UNITS`) | the API ceilings and units are the controller's by [decision](decisions/field-specs-from-dtos.md); the `.proto` carries what the model carries |
| `ComparisonRequest`, `WhatIfRequest`, `CashLadderRequest` | hand-written, mirroring the `.proto`'s messages of the same name; a test pins the property names to the `.proto` and the item bounds to the controller | the `.proto` gives their shape, not the merge semantics (`{**base, **candidate}`), `minProperties: 1` on a variation, or `minimum: 0` on an amount |
| paths, parameters, status codes, headers, `Error` and its `code` enums, the response schemas (`Created`, `SimulationResource`, `Summary`, `Comparison`, `SimulationPayload` and its sections), every example | hand-written from the contract | design, not derivable from a data schema — see below |

### Why no tool generates the rest from the `.proto`

- The existing protoc plugins (`protoc-gen-openapi` from gnostic, grpc-gateway's
  `protoc-gen-openapiv2`) derive *operations* from `service` definitions annotated with
  `google.api.http`. This API has no service in the `.proto` and is not a gRPC transcoding:
  the resource routes (`{path}` into the payload tree, `?fields=`, `?ids=&relative_to=`,
  `Location` headers, the `201`-answers-with-the-`GET` pattern) have no proto counterpart.
- Their *schemas* follow proto3's JSON mapping, which contradicts the contract: property names
  in lowerCamelCase (`listPrice`), `int32` as `integer/int32`, no defaults (proto3 has none —
  ours live in a custom option the plugins do not read), no `maximum`, nullability by message
  wrappers rather than `type: [number, "null"]`, and `"440000"` accepted for a number.
- They are Go binaries, not Python dependencies; the project's toolchain is `pip`.

So the derivation is done by the project's own 150-line generator, reusing the `.proto` reader
of `backend/tools/gen_dto.py`, for the one component a data schema can fully state.

### Why the hand-written part is hand-written

The routes, their status codes and the error semantics are **design** — written in the contract
before any controller existed — and the contract forbids a second source of truth for things the
code already states. Generating the document from Flask decorators (flask-smorest, apiflask,
spectree) would invert that, bring a validation library whose error bodies are not the contract's
(`code`, `field`, `index`, first error in a fixed order), and put the OpenAPI vocabulary in the
controller. Instead the YAML is hand-written and **tests make it as trustworthy as generated
code**.

## The drift guards — `test_openapi.py`

| Guard | What fails when |
|---|---|
| valid OpenAPI 3.1 (`openapi-spec-validator`) | a typo in the document |
| the generated block equals a fresh render (`gen_openapi.py --check`) | the `.proto` changed without running `gen_openapi.py`, or someone edited the block |
| `InputFields` ⇔ `FIELD_SPECS`: same fields in the same order, type, default, unit, group, `maximum`, `maxItems`; `SimulationInput.required` ⇔ `REQUIRED_FIELDS` | the shape layer and the document disagree on a field |
| the request wrappers mirror the `.proto` messages and `MIN_ITEMS`/`MAX_ITEMS` | a wrapper key or a limit changes on one side |
| `Error.code.enum` ⇔ the codes raised in `api_requests.py` plus the Flask-side ones; every per-status enum is a subset; every error example carries a code of its response | a code is added, renamed or misfiled |
| every request example replays through the shape layer and the model with the outcome its `x-expect` states (`201`, or `400`/`422` with `code`, `field`, `index`) | the document promises a refusal the layer does not make, or vice versa |
| every response example validates against its response schema | an example drifts from the schema |
| `Summary` ⇔ `summary_to_dict`; `SimulationPayload` accepts real payloads (with and without balloons) and declares every key (`additionalProperties: false` on every section); `ResolvedInput` accepts `input_to_dict`; comparison and what-if rows built from `what_if_to_dict` validate; `FieldSpec` accepts every row of `field_specs()` | a view changes a key and the document does not follow |

The request examples double as fixtures: each carries `x-expect` (a specification extension,
allowed on Example Objects) with the status and error body it must produce. Adding a case to the
contract's `400` table means adding one example; the test is parametrised over all of them.

## Conventions in the document

- `{path}` is declared as one path parameter although it contains `/`
  (`financing/sac/schedule`); OpenAPI has no templating for that, so the parameter's `pattern`
  and description say it. The concrete `/result`, `/what-if` and `/cash-ladder` paths sit next
  to the templated one, which OpenAPI resolves in favour of the concrete path.
- `GET …/{id}/{path}` answers with "one of the section schemas, or an array of their rows, or any
  subset under `fields`"; that is documented, not encoded as a `oneOf`, because a projection is
  any subset and a schema that accepts everything says nothing.
- `ComparisonRow` lists the summary columns without requiring them (a `?fields=` projection is
  any subset) and forbids unknown ones (`unevaluatedProperties: false`); `Summary`, the
  unprojected object of a resource, requires all of them.
- Per-status error responses narrow `Error.code` with an `allOf` over the shared schema, so a
  client reads under each status exactly the codes it can branch on.
- `version` is the contract's revision (`0.6`); it becomes semver when milestone 5 ships.

## What a schema cannot say

Stated in the contract and quoted in `description`s: the order of checks; finiteness (JSON has no
`NaN`; the rule exists because Python's parser accepts it); `null_not_allowed` as distinct from a
type error; ascending, distinct ladder amounts; `{}` is not a variation; the content-addressed id
and the lifetime; all-or-nothing creation; `overrides` as a diff of resolved inputs and `delta` as
a subtraction; the per-message `422` rules.

## Open points

- **Serving it** (milestone 5): `GET /api/openapi.yaml` and a static `docs.html` loading
  Swagger UI from a pinned CDN; once the controller exists, a test-client fixture can validate
  every response against the schema of its status (the last guard of the plan).
- **Help text**: the `description` of each input field is the `.proto` comment; the CLI's `HELP`
  in `cli_controller.py` says the same thing in other words — the contract's open question on one
  source for help text.
- **Generating the wrappers too**: `ComparisonRequest` & co. could be rendered from the `.proto`
  with their limits merged in, as `InputFields` is, if they ever change more than once.
