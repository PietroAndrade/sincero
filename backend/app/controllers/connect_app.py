"""
The Connect applications of the `Simulations` service, configured as docs/api-contract.md
("Transport") says: Protobuf binary and JSON, and **unknown JSON keys refused** — the proto3
JSON convention (and `connectrpc`'s default) is to ignore them, which would let a misspelt
field (`list_prise`) silently fall back to its default.

    asgi_app(service)    the ASGI application (uvicorn, …) of an async `Simulations`
    wsgi_app(service)    the WSGI application of a sync `SimulationsSync`

The service implementation (milestone 5) validates each request with
`connect_errors.validate` and runs the model through `connect_errors.simulate_one` /
`simulate_all`, so every error leaves as the contract's Connect error.
"""
from __future__ import annotations

from typing import Any

from connectrpc.codec import proto_binary_codec, proto_json_codec

from app.gen.sincero.simulations_service_connect import (Simulations, SimulationsASGIApplication, SimulationsSync,
                                                         SimulationsWSGIApplication)


def codecs() -> list:
    return [proto_binary_codec(), proto_json_codec(ignore_unknown_fields=False)]


def asgi_app(service: Simulations, **options: Any) -> SimulationsASGIApplication:
    return SimulationsASGIApplication(service, codecs=codecs(), **options)


def wsgi_app(service: SimulationsSync, **options: Any) -> SimulationsWSGIApplication:
    return SimulationsWSGIApplication(service, codecs=codecs(), **options)
