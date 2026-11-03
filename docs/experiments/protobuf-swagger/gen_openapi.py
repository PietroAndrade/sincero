"""
Experiment: generate the `components.schemas` of an OpenAPI 3.1 document from a .proto
descriptor (no Go plugin, no gRPC) and merge them into a hand-written skeleton of paths.

    python3 -m venv /tmp/pbenv && /tmp/pbenv/bin/pip install protobuf pyyaml jsonschema openapi-spec-validator
    protoc -I. --python_out=. sincero_options.proto simulation_input.proto
    PYTHONPATH=../../../backend /tmp/pbenv/bin/python gen_openapi.py     # writes openapi.yaml
    PYTHONPATH=../../../backend /tmp/pbenv/bin/python check.py
"""
from __future__ import annotations

import json

import yaml
from google.protobuf.descriptor import FieldDescriptor as F

import sincero_options_pb2 as opt
import simulation_input_pb2 as pb

TYPES = {F.TYPE_DOUBLE: "number", F.TYPE_INT32: "integer", F.TYPE_STRING: "string"}


def field_schema(f: F) -> dict:
    o = f.GetOptions()
    ext = o.Extensions
    base: dict = {"type": TYPES[f.type]}
    if f.is_repeated:
        item = base
        base = {"type": "array", "items": item}
        if ext[opt.max_items]:
            base["maxItems"] = ext[opt.max_items]
    elif f.has_presence and not ext[opt.required] and ext[opt.default_json] == "" and f.name in NULLABLE:
        base = {"type": [base["type"], "null"]}
    if ext[opt.maximum]:
        (base["items"] if f.is_repeated else base)["maximum"] = ext[opt.maximum]
    if ext[opt.default_json]:
        base["default"] = json.loads(ext[opt.default_json])
    if ext[opt.unit]:
        base["description"] = f"Unit: {ext[opt.unit]}."
    return base


# proto3 cannot say "nullable"; the experiment lists them here (an honest gap, see the notes).
NULLABLE = {"developer_installment", "pre_approved_credit"}


def message_schema(m, *, overrides: bool = False) -> dict:
    props, required = {}, []
    for f in m.fields:
        if f.message_type is not None:
            ref = "InputOverrides" if f.message_type.name == "SimulationInput" else f.message_type.name
            props[f.name] = ({"type": "array", "items": {"$ref": f"#/components/schemas/{ref}"},
                              "minItems": 1, "maxItems": f.GetOptions().Extensions[opt.max_items]}
                             if f.is_repeated else {"$ref": f"#/components/schemas/{ref}"})
        else:
            props[f.name] = field_schema(f)
        if f.GetOptions().Extensions[opt.required] and not overrides:
            required.append(f.name)
    s = {"type": "object", "additionalProperties": False, "properties": props}
    if required:
        s["required"] = required
    if overrides:
        s["minProperties"] = 1
    return s


def build() -> dict:
    sim = pb.DESCRIPTOR.message_types_by_name["SimulationInput"]
    cmp_ = pb.DESCRIPTOR.message_types_by_name["ComparisonRequest"]
    error = {"type": "object", "additionalProperties": False, "required": ["error", "code"],
             "properties": {"error": {"type": "string"}, "code": {"type": "string"},
                            "field": {"type": "string"}, "index": {"type": "integer"}}}
    return {
        "openapi": "3.1.0",
        "info": {"title": "SINCERO API (experiment)", "version": "0.0.1"},
        "paths": {
            "/api/simulations": {"post": {
                "operationId": "createSimulation", "summary": "Create a simulation",
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/SimulationInput"},
                    "examples": {"RA": {"value": {"name": "RA", "list_price": 440000, "months_remaining": 19,
                                                  "fgts_upfront": 13000, "developer_installment": 2500,
                                                  "balloon_months": [6, 12]}}}}}},
                "responses": {"201": {"description": "Created"},
                              "400": {"description": "Shape error", "content": {"application/json": {
                                  "schema": {"$ref": "#/components/schemas/Error"}}}}}}},
            "/api/comparisons": {"post": {
                "operationId": "createComparison", "summary": "Compare candidates",
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/ComparisonRequest"}}}},
                "responses": {"200": {"description": "OK"}}}},
        },
        "components": {"schemas": {
            "SimulationInput": message_schema(sim),
            "InputOverrides": message_schema(sim, overrides=True),
            "ComparisonRequest": message_schema(cmp_),
            "Error": error,
        }},
    }


if __name__ == "__main__":
    with open("openapi.yaml", "w") as fh:
        yaml.safe_dump(build(), fh, sort_keys=False, allow_unicode=True)
    print("wrote openapi.yaml")
