# Experiment: protobuf from TypeScript and C#

The question (docs/protobuf-languages.md): the Python backend needs a custom generator to turn
`backend/proto/sincero/simulation_input.proto` into DTOs and a custom generator to turn it into
OpenAPI schemas — would another language make protobuf a better fit?

| Directory | Status |
|---|---|
| [`typescript/`](typescript/) | run end to end (generate, experiment, rules, 7 tests) |
| [`csharp/`](csharp/) | code generation run; build and tests written but **not run** (NuGet unreachable from the sandbox) |
| [`python/`](python/) | run end to end (experiment, rules, 15 tests) — the backend's language, for a like-for-like comparison |
| [`connect/`](connect/) | run end to end: a draft `service` in the `.proto`, a Python Connect server on the real model, a TypeScript client over Connect+JSON, Connect+binary and gRPC-Web — the evidence of [`../../decisions/api-protocol-and-language.md`](../../decisions/api-protocol-and-language.md) |
| [`proto/`](proto/) | `sincero_rules.proto`: the model's `422` rules as `buf.validate` constraints, shared by the TypeScript and Python runs; `buf_validate.binpb`: the `buf/validate/validate.proto` descriptor set both compile against |

Both use the backend's `.proto` as is. Findings: [`../../protobuf-languages.md`](../../protobuf-languages.md).
