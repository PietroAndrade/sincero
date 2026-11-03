# Connect round trip: a TypeScript client on a Python server, one `.proto`

The question behind [`docs/decisions/api-protocol-and-language.md`](../../../decisions/api-protocol-and-language.md):
can the backend stay in Python and still serve a browser front-end over a protobuf RPC protocol,
with no proxy, from the same `.proto` the front-end generates its client from? This is the
smallest proof: three RPCs of a draft service, the real model behind them, a generated
TypeScript client over the two protocols a browser can speak.

```bash
./generate.sh                                  # protoc-gen-py + protoc-gen-connectrpc (pip) and protoc-gen-es (npm)
cd ../../../../backend && .venv/bin/pip install connectrpc protoc-gen-py protoc-gen-connectrpc uvicorn
.venv/bin/python -m uvicorn --app-dir ../docs/experiments/protobuf-languages/connect/server connect_server:app --port 8765
cd ../docs/experiments/protobuf-languages/connect/client && npm install && npm start
```

| File | What |
|---|---|
| `proto/sincero/api.proto` | a draft `service Simulations` over the backend's `sincero/simulation_input.proto` (unchanged, referenced in place); idempotent reads marked `NO_SIDE_EFFECTS` so they are plain HTTP `GET`s |
| `generate.sh` | one protoc run, three plugins: Python messages (`protobuf-py`), Python Connect service + client, TypeScript messages + service |
| `server/connect_server.py` | 89 lines: `CreateSimulation`, `GetSimulation`, `GetNode` on the **existing** `simulate` and JSON view; the model's `SimulationError` → `ConnectError(INVALID_ARGUMENT, message)`; `protovalidate` on the request; the JSON codec configured to refuse unknown fields; an ASGI app served by uvicorn |
| `client/client.ts` | the typed client, over Connect+JSON, Connect+binary and gRPC-Web (`@connectrpc/connect-node`; `connect-web` uses the same transports on `fetch`) |
| `server/gen/`, `client/gen/` | generated, committed for reading (2,189 lines for both sides) |
| `output.txt` | the run: curl against the server, then the client over the three protocols |

Observed: the same id from the three protocols (content-addressed); the model's message verbatim in
the error; `NOT_FOUND` for an unknown id; `GetNode?…` over HTTP `GET`. Two things had to be
configured, both recorded in the decision: the Connect JSON codec ignores unknown keys by default,
and `to_json()` drops zero values of implicit-presence fields (`months_remaining: 0` vanished on
the way to the model until the conversion was written against the descriptor's presence).

Versions: `connectrpc` 0.13, `protobuf-py` 0.7, `protoc-gen-py` / `protoc-gen-connectrpc` (pip),
`uvicorn` 0.54, `@connectrpc/connect` 2.2, `@bufbuild/protobuf` 2.16, Node 22.
