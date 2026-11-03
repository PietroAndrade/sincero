#!/usr/bin/env sh
# Generate the Python server/client and the TypeScript client from proto/sincero/api.proto and
# the backend's sincero/simulation_input.proto (unchanged, referenced in place).
# Plugins: protoc-gen-py + protoc-gen-connectrpc (pip, in the backend's venv), protoc-gen-es (npm,
# in ../typescript/node_modules). protoc is grpcio-tools'.
set -e
cd "$(dirname "$0")"
VENV=../../../../backend/.venv
INCLUDE=$($VENV/bin/python -c "import importlib.resources as r; print(r.files('grpc_tools')/'_proto')")
rm -rf server/gen client/gen && mkdir -p server/gen client/gen
$VENV/bin/python -m grpc_tools.protoc -Iproto -I../../../../backend/proto -I"$INCLUDE" \
  --plugin=protoc-gen-py=$VENV/bin/protoc-gen-py --py_out=server/gen \
  --plugin=protoc-gen-connectrpc=$VENV/bin/protoc-gen-connectrpc --connectrpc_out=server/gen \
  --plugin=protoc-gen-es=../typescript/node_modules/.bin/protoc-gen-es --es_out=client/gen --es_opt=target=ts,import_extension=js \
  sincero/api.proto sincero/simulation_input.proto
find server/gen client/gen -type f | xargs wc -l | sort -k2
