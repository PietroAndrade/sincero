"""
A Connect server in Python on the existing model: `connectrpc` (ASGI) + `protobuf-py` messages.
Implements three RPCs of the draft service for the round trip — create, read, read a node —
with the real `simulate` and the real JSON view behind them.

    cd backend && .venv/bin/python -m uvicorn --app-dir ../docs/experiments/protobuf-languages/connect/server connect_server:app --port 8765
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / "gen"), str(HERE.parents[4] / "backend")]

import protovalidate                                                     # noqa: E402
from connectrpc._codec import proto_binary_codec, proto_json_codec       # noqa: E402
from connectrpc.code import Code                                         # noqa: E402
from connectrpc.errors import ConnectError                               # noqa: E402
from connectrpc.request import RequestContext                            # noqa: E402
from sincero import api_connect, api_pb                                  # noqa: E402  (generated)
from sincero.simulation_input_pb import SimulationInput                  # noqa: E402  (generated from the backend's .proto)

from app.models import SimulationError, simulate                         # noqa: E402  the model, unchanged
from app.views import input_from_dict, simulation_to_dict, summary_to_dict   # noqa: E402  the views, unchanged

STORE: dict[str, SimulationInput] = {}
DEFAULTS = {"name": "CUSTOM"}


def to_model_input(msg: SimulationInput):
    """
    protobuf-py message -> the model's SimulationInput (defaults applied by the DTOs).
    A field with explicit presence (`optional`) that is not set is left out, so the DTO's default
    applies; an implicit-presence field is always passed — `months_remaining: 0` must reach the
    model and be refused there, not vanish (`to_json` drops zero values).
    """
    data = {f.name: getattr(msg, f.name) for f in SimulationInput.desc().fields
            if f.presence != f.presence.EXPLICIT or msg.has_field(f.name)}
    data["balloon_months"] = list(data["balloon_months"])
    return input_from_dict({**DEFAULTS, **data})


class Service(api_connect.Simulations):
    async def create_simulation(self, request: SimulationInput, ctx: RequestContext) -> api_pb.Created:
        try:
            protovalidate.validate(request)                                 # rules in the .proto, if any
            result = simulate(to_model_input(request))                      # the model's own rules -> SimulationError
        except SimulationError as exc:
            raise ConnectError(Code.INVALID_ARGUMENT, str(exc)) from exc    # the 422 of the contract
        except protovalidate.ValidationError as exc:
            raise ConnectError(Code.INVALID_ARGUMENT, str(exc)) from exc
        sim_id = hashlib.md5(result.input.to_dict().__repr__().encode()).hexdigest()   # content-addressed
        STORE[sim_id] = request
        return api_pb.Created(id=sim_id)

    async def get_simulation(self, request: api_pb.GetSimulationRequest, ctx: RequestContext) -> api_pb.SimulationResource:
        if request.id not in STORE:
            raise ConnectError(Code.NOT_FOUND, f"simulation not found: {request.id}")
        result = simulate(to_model_input(STORE[request.id]))
        s = summary_to_dict(result)
        return api_pb.SimulationResource(id=request.id, input=STORE[request.id],
                                         summary=api_pb.Summary(id=request.id, name=s["name"], total_cost=s["total_cost"]))

    async def get_node(self, request: api_pb.GetNodeRequest, ctx: RequestContext) -> api_pb.Node:
        if request.id not in STORE:
            raise ConnectError(Code.NOT_FOUND, f"simulation not found: {request.id}")
        node = simulation_to_dict(simulate(to_model_input(STORE[request.id])))
        for segment in request.path.split("/"):
            if not isinstance(node, dict) or segment not in node:
                raise ConnectError(Code.NOT_FOUND, f"no such node: {request.path}")
            node = node[segment]
        if request.fields:
            node = {k: v for k, v in node.items() if k in request.fields}
        return api_pb.Node(json=json.dumps(node).encode())

    async def get_comparison(self, request, ctx): raise ConnectError(Code.UNIMPLEMENTED, "not in the smoke test")
    async def create_comparison(self, request, ctx): raise ConnectError(Code.UNIMPLEMENTED, "not in the smoke test")
    async def create_what_if(self, request, ctx): raise ConnectError(Code.UNIMPLEMENTED, "not in the smoke test")
    async def create_cash_ladder(self, request, ctx): raise ConnectError(Code.UNIMPLEMENTED, "not in the smoke test")
    async def list_fields(self, request, ctx): raise ConnectError(Code.UNIMPLEMENTED, "not in the smoke test")


# The JSON codec ignores unknown fields by default (proto3 JSON convention); the contract's
# `unknown_field` rule wants them refused, and the codec can be told so.
app = api_connect.SimulationsASGIApplication(
    Service(), codecs=[proto_binary_codec(), proto_json_codec(ignore_unknown_fields=False)])
