# Experiment: protobuf as the schema, OpenAPI + Swagger UI as the document (no gRPC)

*Run on 2026-11-03. Question: can one `.proto` declare the input fields, with the OpenAPI 3.1
schemas generated from it and shown in Swagger UI, without gRPC and without putting protobuf in
the request path?*

## Files

| File | Role |
|---|---|
| `sincero_options.proto` | custom field options: `required`, `maximum`, `unit`, `default_json`, `max_items` |
| `simulation_input.proto` | `SimulationInput` (16 fields) and `ComparisonRequest`, annotated with those options |
| `gen_openapi.py` | reads the compiled descriptor (`protobuf` only) and writes `openapi.yaml` |
| `check.py` | validates the document and compares it with `FIELD_SPECS` and the shape layer |
| `docs.html` | Swagger UI 5.17.14 from cdnjs, pointing at `openapi.yaml` |
| `openapi.yaml`, `*_pb2.py` | generated; kept so the result can be read without running anything |

Reproduce: the docstring of `gen_openapi.py`.

## Result

| Question | Answer |
|---|---|
| Does `.proto` → OpenAPI 3.1 work without Go, gRPC or `grpcio-tools`? | **Yes.** `protoc` (or `grpcio-tools`) compiles the `.proto`; a ~110-line script walks `DESCRIPTOR` and emits `components.schemas`. Runtime dependency: `protobuf` (dev/build only if the script is a build step). |
| Is the document valid OpenAPI 3.1? | **Yes**, `openapi-spec-validator` accepts it. |
| Does the generated schema match `FIELD_SPECS` (names, order, types, defaults, limits, required)? | **Yes**, after fixing five defaults I had mistyped in the `.proto` (`bank_rate_pa`, `term_months`, `registry_pct`, `pro_soluto_months`, `balloon_months`). The check named each one — which is the point and the cost: **the defaults and limits are a second declaration**. |
| Does the generated schema refuse and accept the same bodies as `api_requests.py`? | **11 of 11** bodies (strings, `true`, `19.5`, `19.0`, unknown key, missing required, `null` on a non-nullable and a nullable field, 61 balloons, months 5000). JSON Schema, unlike proto3's JSON mapping, is strict about types. |
| Swagger UI | `docs.html` is the plan's static page, unchanged except for the cdnjs URL (HTTP 200). **Not rendered in a browser in this run.** |
| Could not be tried | `protoc-gen-openapi` (gnostic) and `protoc-gen-openapiv2` (grpc-gateway): both are Go, and the Go toolchain download was refused in this session. They would give paths/operations from `google.api.http` annotations, which is gRPC-gateway territory anyway; the script above covers only `components.schemas`. |

## What it shows about "protobuf, without gRPC"

1. **Protobuf works as the declaration of the schema, not as the validator.** The earlier
   experiment ([`../protobuf-validation/`](../protobuf-validation/)) showed that `ParseDict`
   cannot enforce the contract's strict JSON types. The schema *generated from* the `.proto`
   can, because JSON Schema can. So: `.proto` → `openapi.yaml` (JSON Schema) → Swagger UI and
   tests; the hand-written shape layer keeps the request path.
2. **proto3 cannot say four things the contract needs**, so they ride on custom options or a
   side list: `required` (option), `maximum`/`maxItems` (options), defaults (option holding a
   JSON literal), and **nullable** (no option written: `NULLABLE` is a set in `gen_openapi.py`,
   because `optional double` means "may be absent", not "may be `null`").
3. **`SimulationInput` would have three declarations** — the DTOs, the `.proto`, and (if the
   plan's hand-written YAML stays) the YAML. `check.py` is the drift guard that keeps the first
   two equal, and it caught five real mismatches on its first run. The alternative is to make
   the `.proto` the only declaration and generate the DTOs from it, which contradicts
   [`decisions/field-specs-from-dtos.md`](../../decisions/field-specs-from-dtos.md) and is a
   model-layer change; not tried.
4. **Paths, responses and examples stay hand-written** (here, a 40-line skeleton in the
   script). Only the schemas come from the `.proto`.
5. **The TypeScript benefit is untested**: `openapi-typescript` on the generated YAML, or
   `ts-proto` on the `.proto` directly, are the two routes for milestone 6.2.
