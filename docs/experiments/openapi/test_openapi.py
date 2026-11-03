"""
`openapi.yaml` is as trustworthy as the code: it is valid OpenAPI 3.1, its generated block is
what the .proto says, its input schema is the shape layer's field specs, its error codes are
the codes the code raises, its response schemas accept the real payloads, and every request
example is accepted or refused exactly as its `x-expect` says.
"""
import re
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate as validate_openapi

from app.controllers import api_requests
from app.controllers.api_requests import (FIELD_SPECS, MAX_BALLOONS, MAX_ITEMS, MIN_ITEMS, REQUIRED_FIELDS,
                                          UPPER_BOUNDS, ApiError, cash_ladder_inputs, comparison_inputs,
                                          field_specs, simulate_all, simulate_one, simulation_input,
                                          what_if_inputs)
from app.models import cash_ladder
from app.views import input_to_dict, simulation_to_dict, summary_to_dict, what_if_to_dict
from tools.gen_dto import PROTO, PROTO_DIR, compile_proto

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_openapi                                       # noqa: E402
from gen_openapi import TARGET, render_block, split      # noqa: E402

SPEC = yaml.safe_load(TARGET.read_text(encoding="utf-8"))
SCHEMAS = SPEC["components"]["schemas"]

# Codes the Flask controller (milestone 5) raises on its own, per the contract's status table;
# the shape layer's codes are read from its source below.
FLASK_CODES = {"malformed_json", "not_found", "method_not_allowed", "payload_too_large", "unsupported_media_type",
               "internal_error"}

RA = {"name": "RA", "list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000,
      "developer_installment": 2500, "balloon_months": [6, 12]}


def resolve(node):
    """Follow a `$ref` inside the document (responses, examples, request bodies)."""
    while isinstance(node, dict) and "$ref" in node and len(node) == 1:
        target = SPEC
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def validator(schema) -> Draft202012Validator:
    """A JSON Schema validator for `schema`, with `#/components/schemas/…` refs resolved in this document."""
    root = {**schema, "components": {"schemas": SCHEMAS}}
    return Draft202012Validator(root, format_checker=FormatChecker())


def assert_valid(schema, instance):
    errors = sorted(validator(schema).iter_errors(instance), key=lambda e: list(e.absolute_path))
    assert not errors, "\n".join(f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:200]}" for e in errors)


def component(name):
    return {"$ref": f"#/components/schemas/{name}"}


# ----- the document ----------------------------------------------------------------------------
def test_document_is_valid_openapi_31():
    assert SPEC["openapi"] == "3.1.0"
    validate_openapi(SPEC)


def test_generated_block_is_up_to_date(capsys):
    assert split(TARGET.read_text(encoding="utf-8"))[1] == render_block(), "openapi.yaml is stale: run gen_openapi.py"
    assert gen_openapi.main(["--check"]) == 0 and capsys.readouterr().out == ""


def test_every_operation_has_an_id_a_tag_and_the_error_responses():
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method == "parameters":
                continue
            assert op["operationId"] and op["tags"], (path, method)
            assert "500" in op["responses"], (path, method)
            if method == "post":
                assert {"400", "413", "415", "422"} <= set(op["responses"]), (path, method)
                assert "requestBody" in op


# ----- the input schema is the shape layer's field specs ------------------------------------------
JSON_TYPE = {"string": "string", "number": "number", "integer": "integer",
             "number|null": ["number", "null"], "integer[]": "array"}


def test_input_fields_match_the_field_specs():
    props = SCHEMAS["InputFields"]["properties"]
    assert list(props) == [s.name for s in FIELD_SPECS]                 # every field, in DTO order, nothing else
    assert SCHEMAS["InputFields"]["additionalProperties"] is False
    assert SCHEMAS["SimulationInput"]["required"] == list(REQUIRED_FIELDS)
    for spec in FIELD_SPECS:
        prop = props[spec.name]
        assert prop["type"] == JSON_TYPE[spec.type], spec.name
        assert prop.get("default") == spec.default, spec.name
        assert prop.get("x-unit") == spec.unit, spec.name
        assert prop["x-group"] == spec.group, spec.name
        assert prop.get("maximum") == UPPER_BOUNDS.get(spec.name), spec.name
        if spec.type == "integer[]":
            assert prop["items"] == {"type": "integer"} and prop["maxItems"] == MAX_BALLOONS
        assert prop["description"], spec.name
    # every field-spec row of `GET /api/fields` is a valid FieldSpec
    for row in field_specs():
        assert_valid(component("FieldSpec"), row)


def test_request_wrappers_mirror_the_proto_and_the_item_limits():
    fds = compile_proto(PROTO, [PROTO_DIR])
    messages = {m.name: m for f in fds.file if f.name == PROTO for m in f.message_type}
    for name, array_key in [("ComparisonRequest", "candidates"), ("WhatIfRequest", "variations"),
                            ("CashLadderRequest", "amounts")]:
        schema = SCHEMAS[name]
        assert list(schema["properties"]) == [f.name for f in messages[name].field], name
        assert schema["required"] == [array_key] and schema["additionalProperties"] is False
        items = schema["properties"][array_key]
        assert (items["minItems"], items["maxItems"]) == (MIN_ITEMS, MAX_ITEMS), name
    assert SCHEMAS["CashLadderRequest"]["properties"]["amounts"]["items"]["maximum"] == UPPER_BOUNDS["cash_upfront"]


# ----- error codes ---------------------------------------------------------------------------------
def test_error_codes_are_exactly_the_codes_the_code_raises():
    source = Path(api_requests.__file__).read_text(encoding="utf-8")
    raised = set(re.findall(r'(?:_bad_request|ApiError)\(\s*(?:\d+,\s*)?"([a-z_]+)"', source))
    assert raised, "no codes found in api_requests.py"
    assert set(SCHEMAS["Error"]["properties"]["code"]["enum"]) == raised | FLASK_CODES
    assert SCHEMAS["Error"]["additionalProperties"] is False
    for name, response in SPEC["components"]["responses"].items():
        narrowed = response["content"]["application/json"]["schema"]["allOf"][1]["properties"]["code"]["enum"]
        assert set(narrowed) <= raised | FLASK_CODES, name
        for example in response["content"]["application/json"].get("examples", {}).values():
            assert example["value"]["code"] in narrowed, (name, example)
            assert_valid(component("Error"), example["value"])


# ----- request examples replay through the shape layer ----------------------------------------------
def request_examples():
    for body_name, body in SPEC["components"]["requestBodies"].items():
        for example_name, example in body["content"]["application/json"]["examples"].items():
            yield pytest.param(body_name, example["value"], example["x-expect"], id=f"{body_name}:{example_name}")


def run(body_name, body):
    base = simulation_input({"list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000})
    if body_name == "SimulationInput":
        return [simulate_one(simulation_input(body))]
    if body_name == "ComparisonRequest":
        return simulate_all(comparison_inputs(body))
    if body_name == "WhatIfRequest":
        return simulate_all(what_if_inputs(body, base))
    if body_name == "CashLadderRequest":
        return simulate_all(cash_ladder_inputs(body, base))
    raise AssertionError(body_name)


@pytest.mark.parametrize("body_name, body, expect", list(request_examples()))
def test_request_examples_are_accepted_or_refused_as_documented(body_name, body, expect):
    if expect["status"] == 201:
        assert run(body_name, body)
        schema = SPEC["components"]["requestBodies"][body_name]["content"]["application/json"]["schema"]
        assert_valid(schema, body)
        return
    with pytest.raises(ApiError) as info:
        run(body_name, body)
    err = info.value.to_dict()
    assert (info.value.status, err["code"], err.get("field"), err.get("index")) == \
           (expect["status"], expect["code"], expect.get("field"), expect.get("index")), err


def test_every_request_example_says_what_to_expect():
    for body_name, body, expect in (p.values for p in request_examples()):
        assert set(expect) <= {"status", "code", "field", "index"} and expect["status"] in (201, 400, 422), body_name
        assert (expect["status"] == 201) == ("code" not in expect), body_name


# ----- response schemas accept the real payloads ----------------------------------------------------
@pytest.fixture(scope="module")
def ra():
    return simulate_one(simulation_input(RA))


def test_summary_is_summary_to_dict(ra):
    summary = summary_to_dict(ra)
    assert SCHEMAS["Summary"]["required"] == list(summary)
    assert list(SCHEMAS["SummaryColumns"]["properties"]) == list(summary)
    assert_valid(component("Summary"), summary)


def test_payload_is_simulation_to_dict(ra):
    assert_valid(component("SimulationPayload"), simulation_to_dict(ra))
    no_balloons = simulate_one(simulation_input({"list_price": 300000, "months_remaining": 4, "cash_upfront": 100000,
                                                 "pre_approved_credit": 150000, "term_months": 12}))
    assert_valid(component("SimulationPayload"), simulation_to_dict(no_balloons))
    assert list(SCHEMAS["SimulationPayload"]["properties"]) == list(simulation_to_dict(ra))
    assert_valid(component("ResolvedInput"), input_to_dict(ra.input))


def test_comparison_rows_and_what_if_rows_validate(ra):
    row = {"id": "3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f", "href": "/api/simulations/3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f",
           **summary_to_dict(ra)}
    assert_valid(component("ComparisonRow"), row)
    base = simulation_input({"list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000})
    ladder = what_if_to_dict(cash_ladder(base, [0, 30000, 75000, 100000]))
    rows = [{**row, **s["summary"], "overrides": s["overrides"], "delta": s["delta"]} for s in ladder["scenarios"]]
    what_if = {"href": "/api/comparisons?ids=a,b,c&relative_to=a", "relative_to": row, "rows": rows}
    assert_valid(component("Comparison"), what_if)
    with pytest.raises(AssertionError, match="unexpected"):
        assert_valid(component("ComparisonRow"), {**row, "colour": "red"})     # strict on names, loose on presence


def test_simulation_resource_example_shape(ra):
    payload = simulation_to_dict(ra)
    sections = {name: {"href": f"/api/simulations/x/{name}",
                       "fields": {k: (f"array[{len(v)}]" if isinstance(v, list) else "object" if isinstance(v, dict)
                                      else "null" if v is None else "string" if isinstance(v, str) else "number")
                                  for k, v in node.items()}}
                for name, node in payload.items()}
    sections["result"] = {"href": "/api/simulations/x/result", "fields": None}
    resource = {"id": "3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f", "href": "/api/simulations/3f9c2b7e1a4d5c6b8e0f1a2b3c4d5e6f",
                "created_at": "2026-03-04T15:02:11Z", "expires_at": "2026-03-04T16:02:11Z",
                "input": payload["input"], "summary": summary_to_dict(ra), "sections": sections}
    assert_valid(component("SimulationResource"), resource)


def response_examples():
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method == "parameters":
                continue
            for status, response in op["responses"].items():
                response = resolve(response)
                media = response.get("content", {}).get("application/json", {})
                for name, example in media.get("examples", {}).items():
                    yield pytest.param(media["schema"], resolve(example)["value"], id=f"{method.upper()} {path} {status} {name}")


@pytest.mark.parametrize("schema, value", list(response_examples()))
def test_response_examples_validate_against_their_schema(schema, value):
    assert_valid(schema, value)
