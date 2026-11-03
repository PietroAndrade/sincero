# Python × protobuf — experiment

The same experiment as [`../typescript`](../typescript) and [`../csharp`](../csharp), in the
backend's own language, so the three compare like for like. Uses
`backend/proto/sincero/simulation_input.proto` unchanged and the backend's virtualenv.

```bash
cd backend
.venv/bin/pip install protovalidate                                            # the one extra package
.venv/bin/python ../docs/experiments/protobuf-languages/python/experiment.py   # the option; resolve(); the contract's bodies; timing
.venv/bin/python ../docs/experiments/protobuf-languages/python/rules.py        # the rules in the .proto, enforced
.venv/bin/python -m pytest ../docs/experiments/protobuf-languages/python -q -p no:cacheprovider   # 15 small tests
```

| File | What |
|---|---|
| `_setup.py` | compiles the two protos into a temporary directory with `grpcio-tools` and imports them (`buf/validate/validate.proto` comes from `../proto/buf_validate.binpb`, as for TypeScript) |
| `experiment.py` | the generated message used as the DTO (which the application does **not** do — see the first test for why); `FIELDS` (defaults, group, nullable from the option through the descriptor); `resolve()`; `split()`; the contract's `400` bodies through `json_format.ParseDict`, next to the application's hand-written shape layer on the same bodies |
| `rules.py` | `../proto/sincero_rules.proto` enforced by `protovalidate` 2.1 — same file, same violations as TypeScript's `rules.ts` |
| `test_experiment.py` | the tests (pytest) |
| `output.txt`, `rules-output.txt`, `test-output.txt` | the three runs, as run |

Notes. `protovalidate` 2.x for Python is built on `protobuf-py` (buf's runtime) but validates
`google.protobuf` messages directly; it pulled in `protobuf-py` 0.7 and nothing else. The
generated `simulation_input_pb2.py` is a serialized descriptor, not readable code — the
message classes are built at import; its types are only visible through a `.pyi` stub
(`--pyi_out`), which the application does not generate because it does not use the messages at
runtime.

Run with Python 3.12, `protobuf` 7.36, `grpcio-tools` 1.76, `protovalidate` 2.1.
