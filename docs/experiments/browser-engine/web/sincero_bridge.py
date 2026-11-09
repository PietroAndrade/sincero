"""
The bridge between JavaScript and the unchanged Python engine, for the in-browser Python runtimes
(Pyodide, Brython). It calls the same entry points as `backend/support/gateway.py::EngineGateway`
(`input_from_dict`, `simulate`, the JSON view) and answers with one JSON string:

    {"ok": true, "value": <payload>}
    {"ok": false, "kind": "rejected", "error": "<SimulationError message, verbatim>"}
    {"ok": false, "kind": "invalid_shape", "error": "..."}      (TypeError: unknown or missing field)
"""
import json

from app.models import SimulationError, cash_ladder, compare, simulate
from app.views import comparison_to_dict, input_from_dict, simulation_to_dict, what_if_to_dict


def call(kind, request_json):
    request = json.loads(request_json)
    try:
        if kind == "simulate":
            value = simulation_to_dict(simulate(input_from_dict(request["input"])))
        elif kind == "compare":
            value = comparison_to_dict(compare([input_from_dict(r) for r in request["inputs"]]))
        elif kind == "cash_ladder":
            value = what_if_to_dict(cash_ladder(input_from_dict(request["input"]), request["amounts"]))
        else:
            raise ValueError(f"unknown call: {kind}")
    except SimulationError as exc:
        return json.dumps({"ok": False, "kind": "rejected", "error": str(exc)})
    except TypeError as exc:
        return json.dumps({"ok": False, "kind": "invalid_shape", "error": str(exc)})
    return json.dumps({"ok": True, "value": value})
