"""
docs/api-contract.md against what it describes: the revision it states is the one
simulations_service.proto states, and the tables a reader relies on — RPCs, input fields,
validation rule ids, errors, limits — are the descriptors' and the code's. Changing the service
without the contract (or the contract without the service) fails here.
"""
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("connectrpc")
from protobuf.wkt.google.protobuf.descriptor_pb import MethodOptions  # noqa: E402
from protovalidate._gen.buf.validate.validate_pb import ext_field, ext_message  # noqa: E402

from app.controllers import connect_errors  # noqa: E402
from app.controllers.api_requests import field_specs  # noqa: E402
from app.gen.sincero import simulation_input_pb, simulation_result_pb, simulations_service_pb  # noqa: E402
from app.gen.sincero.simulations_service_connect import Simulations  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "docs" / "api-contract.md"
SERVICE_PROTO = REPO / "backend" / "proto" / "sincero" / "simulations_service.proto"
TEXT = CONTRACT.read_text(encoding="utf-8")
FILES = [simulation_input_pb.SimulationInput.desc().file, simulation_result_pb.Summary.desc().file,
         simulations_service_pb.Simulation.desc().file]


def section(title: str) -> str:
    """The text of one `## title` section."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", TEXT, re.M | re.S)
    assert match, f"no section '## {title}' in {CONTRACT.name}"
    return match.group(1)


def table(text: str) -> list[list[str]]:
    """The rows of the first Markdown table in `text`, header and rule excluded; `\\|` unescaped."""
    rows = [line for line in text.splitlines() if line.startswith("|")]
    cells = [[c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)[1:-1]] for row in rows]
    return cells[2:]


def code(cell: str) -> str:
    return cell.strip("`")


# ----- the revision -------------------------------------------------------------------------------
def contract_revision() -> int:
    match = re.search(r"^\*Revision (\d+) — \d{4}-\d{2}-\d{2}\.", TEXT, re.M)
    assert match, "the contract must open with '*Revision N — YYYY-MM-DD.'"
    return int(match.group(1))


def test_the_contract_and_the_service_proto_state_the_same_revision():
    match = re.search(r"Contract: docs/api-contract\.md, revision (\d+)\.", SERVICE_PROTO.read_text(encoding="utf-8"))
    assert match, "simulations_service.proto must state the contract revision it implements"
    assert int(match.group(1)) == contract_revision()


def test_the_revision_history_ends_with_the_current_revision():
    revisions = [int(row[0]) for row in table(section("Revision history"))]
    assert revisions[0] == contract_revision()
    assert revisions == sorted(revisions, reverse=True)


# ----- the RPCs -----------------------------------------------------------------------------------
def test_the_rpc_table_is_the_service():
    documented = [(code(r[0]), code(r[1]), code(r[2]), r[3]) for r in table(section("RPCs"))]
    actual = [(m.name, m.input.name, m.output.name,
               "GET" if m.idempotency == MethodOptions.IdempotencyLevel.NO_SIDE_EFFECTS else "POST")
              for m in Simulations.desc().methods]
    assert documented == actual


# ----- the input fields ------------------------------------------------------------------------------
def test_the_input_table_is_list_fields():
    documented = [[code(row[0]), *row[1:]] for row in table(section("Inputs"))]
    expected = [[spec["name"], spec["group"], spec["type"], "yes" if spec["required"] else "no",
                 "" if spec["required"] else f"`{json.dumps(spec['default'])}`", spec["unit"] or ""]
                for spec in field_specs()]
    assert documented == expected


# ----- validation ------------------------------------------------------------------------------------
def cel_ids(value) -> set[str]:
    """Every `cel` rule id in a rules JSON value, at any depth."""
    if isinstance(value, dict):
        found = {c["id"] for c in value.get("cel", [])}
        return found.union(*(cel_ids(v) for k, v in value.items() if k != "cel"))
    if isinstance(value, list):
        return set().union(*(cel_ids(v) for v in value)) if value else set()
    return set()


def custom_rules_in_the_protos() -> set[str]:
    """The ids of the CEL rules declared in sincero/*.proto: on messages and on fields."""
    ids = set()
    for message in (m for file in FILES for m in file.messages):
        options = message.proto.options
        if options is not None and ext_message in options:
            ids |= cel_ids(json.loads(options[ext_message].to_json()))
        for field in message.fields:
            options = field.proto.options
            if options is not None and ext_field in options:
                ids |= cel_ids(json.loads(options[ext_field].to_json()))
    return ids


def test_every_custom_rule_of_the_protos_is_documented():
    documented = {code(rule_id.strip()) for row in table(section("Validation").split("rule ids as they appear", 1)[1])
                  for rule_id in row[2].split(",")}
    custom = custom_rules_in_the_protos()
    assert custom == {"candidates.list_price", "candidates.months_remaining", "variation.not_empty"}
    assert custom <= documented


def test_every_list_limit_in_the_protos_is_the_documented_one():
    limits = section("API limits")
    assert "| items in `ids`, `candidates`, `variations`, `amounts` | 1 to 20 | `.proto` |" in limits
    lists = {("GetComparison", "ids"), ("CreateComparison", "candidates"), ("CreateWhatIf", "variations"),
             ("CreateCashLadder", "amounts")}
    for method in Simulations.desc().methods:
        for field in method.input.fields:
            if (method.name, field.name) in lists:
                rules = json.loads(field.proto.options[ext_field].to_json())["repeated"]
                assert (rules["minItems"], rules["maxItems"]) == ("1", "20"), f"{method.name}.{field.name}"


# ----- errors --------------------------------------------------------------------------------------------
def test_the_error_table_states_the_mapping_of_the_code():
    rows = {row[0]: row for row in table(section("Errors"))}
    model = rows["a rule of the model (`SimulationError`)"]
    assert model[1] == "`invalid_argument`"
    assert "`google.rpc.ErrorInfo`" in model[2]
    assert f"`reason` `{connect_errors.INVALID_INPUT}`" in model[2] and f"`domain` `{connect_errors.DOMAIN}`" in model[2]
    assert "`metadata.index`" in model[2]
    proto = rows["a `buf.validate` rule of the request"]
    assert proto[1] == "`invalid_argument`" and "`google.rpc.BadRequest`" in proto[2]
    assert rows["an unknown simulation id"][1] == "`not_found`"
    assert connect_errors.not_found("<id>").message in rows["an unknown simulation id"][2]


# ----- links into the contract ---------------------------------------------------------------------------
def anchors() -> set[str]:
    return {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-")
            for h in re.findall(r"^#+ (.+)$", TEXT, re.M)}


def test_every_link_to_a_section_of_the_contract_resolves():
    links = set()
    for path in [*REPO.joinpath("docs").rglob("*.md"), *REPO.joinpath("backend").rglob("*.py"),
                 *REPO.joinpath("backend", "proto").rglob("*.proto")]:
        if "experiments" in path.parts or "gen" in path.parts:
            continue
        links |= set(re.findall(r"api-contract\.md#([\w\-]+)", path.read_text(encoding="utf-8")))
        if path == CONTRACT:
            links |= set(re.findall(r"\]\(#([\w\-]+)\)", TEXT))
    assert links, "expected some links into the contract"
    assert links <= anchors(), sorted(links - anchors())
