# TypeScript × protobuf — experiment

Uses `backend/proto/sincero/simulation_input.proto` unchanged. Everything comes from npm; no
protoc, no Python.

```bash
npm install            # @bufbuild/buf (protoc replacement), @bufbuild/protoc-gen-es, @bufbuild/protobuf,
                       # @bufbuild/protovalidate, typescript
npm run generate       # buf generate ../../../../backend/proto  ->  src/gen/sincero/simulation_input_pb.ts
npm run experiment     # the contract's JSON bodies through fromJson(); the custom option; resolve(); rules
npm test               # 7 small tests pinning the findings (node --test)
```

| File | What |
|---|---|
| `buf.gen.yaml` | the whole code-generation configuration (6 lines) |
| `src/gen/sincero/simulation_input_pb.ts` | generated: one plain object type per message, a schema descriptor per message, the `(sincero.field)` extension — 336 lines, readable, committed for reading |
| `src/experiment.ts` | the generated type as the DTO; `FIELDS` (defaults, group, nullable read from the option with `getOption`); `resolve()` (defaults applied, required checked); `split()` (the three DTOs); the contract's `400` bodies through `fromJson` |
| `../proto/sincero_rules.proto`, `src/rules.ts` | the model's `422` rules as `buf.validate` constraints (+ one CEL expression across fields), enforced by `@bufbuild/protovalidate` |
| `src/test.ts` | the tests |
| `output.txt`, `test-output.txt` | the output of `npm run experiment` and `npm test`, as run |

`npm run generate:rules` compiles `../proto/sincero_rules.proto` with `protoc` (on `PATH`) and
`../proto/buf_validate.binpb` — a descriptor set of `buf/validate/validate.proto` extracted from
the `@bufbuild/protovalidate` package (`buf.build`, which would normally provide it, is not reachable
from the sandbox where this was run). With network access the normal way is a `buf.yaml`
dependency on `buf.build/bufbuild/protovalidate`.

Run on Node 22.21, protobuf-es 2.16, buf 1.74, protovalidate-es 1.3.
