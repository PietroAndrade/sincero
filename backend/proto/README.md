# proto/

- `sincero/simulation_input.proto`: the input fields; `make dto` generates `app/models/input_fields.py` from it.
  `SimulationOverrides` is its partial form (candidates, variations): every field optional and
  validated when set, `BalloonMonths` / `NullableAmount` wrappers so "no balloons" and "back to
  null" can be sent. `tests/test_simulation_overrides.py` keeps it in step with `SimulationInput`.
- `sincero/simulation_result.proto`: the outputs — `SimulationResult` (the ten sections of
  `simulation_to_dict`, field by field) and `Summary` (`summary_to_dict`).
- `sincero/simulations_service.proto`: the API — `service Simulations` (one RPC per route of the
  REST contract), its requests and responses (`Simulation`, `Comparison`, `FieldSpec`, …).
- `google/rpc/error_details.proto`: vendored unmodified from `googleapis-common-protos` 1.76.0
  (Apache-2.0): `ErrorInfo` and `BadRequest`, the details of the service's errors. `connectrpc`
  ships only `google.rpc.Status`.
- `make proto` (`tools/gen_proto.py`) generates the code of these files, committed, never edited by hand:
  - `../frontend/src/gen/`: TypeScript messages and service descriptor (`protoc-gen-es`, installed
    from `../frontend/package-lock.json`);
  - `app/gen/`: Python messages (`protoc-gen-py`, `protobuf-py` runtime) and the Connect service,
    server `Protocol`, ASGI/WSGI apps and clients (`protoc-gen-connectrpc`, `connectrpc` runtime).

  Neither generates `buf/validate/validate.proto`: the TypeScript imports it from
  `@bufbuild/protovalidate`, the Python from `protovalidate`. `make proto-check` regenerates into a
  temporary directory and fails, with the diff, when the committed code is stale; `tests/test_gen_proto.py`
  does the same in `make test`.
- The contract these files implement is `docs/api-contract.md`; `simulations_service.proto` states
  its revision and `tests/test_api_contract.py` fails while the two disagree.
- `buf_validate.binpb`: a descriptor set holding `buf/validate/validate.proto`, extracted from
  `@bufbuild/protovalidate` 1.3. Every `protoc` call that compiles a file importing
  `buf/validate/validate.proto` passes `--descriptor_set_in=<this file>`; that is how `grpcio-tools`'
  `protoc` resolves the import offline. Replace it by a `buf.yaml` dependency when M5 adds `buf`.
