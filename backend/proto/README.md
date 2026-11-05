# proto/

- `sincero/simulation_input.proto`: the input fields; `make dto` generates `app/models/input_fields.py` from it.
- `buf_validate.binpb`: a descriptor set holding `buf/validate/validate.proto`, extracted from
  `@bufbuild/protovalidate` 1.3. Every `protoc` call that compiles a file importing
  `buf/validate/validate.proto` passes `--descriptor_set_in=<this file>`; that is how `grpcio-tools`'
  `protoc` resolves the import offline. Replace it by a `buf.yaml` dependency when M5 adds `buf`.
