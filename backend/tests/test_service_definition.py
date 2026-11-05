"""
The service definition (proto/sincero/simulations_service.proto), read from the generated code:
the RPCs, their request and response types and which are reads; the server `Protocol`s and
clients `protoc-gen-connectrpc` derives from it; the TypeScript descriptor; and the result
messages (proto/sincero/simulation_result.proto) against the JSON view they mirror.
"""
import json
import math
import re

import pytest

pytest.importorskip("connectrpc")
from protobuf.wkt.google.protobuf.descriptor_pb import MethodOptions  # noqa: E402
from app.gen.sincero import simulations_service_connect as connect  # noqa: E402
from app.gen.sincero import simulations_service_pb as service_pb  # noqa: E402
from app.gen.sincero.simulation_result_pb import SimulationResult, Summary  # noqa: E402
from app.models import SimulationInput, simulate  # noqa: E402
from app.models.input_dto import BankCreditData, ContractData  # noqa: E402
from app.views import simulation_to_dict, summary_to_dict  # noqa: E402
from protovalidate._gen.buf.validate.validate_pb import ext_field as rules_ext  # noqa: E402
from tools.gen_proto import TARGETS  # noqa: E402

SERVICE = connect.Simulations.desc()
NO_SIDE_EFFECTS = MethodOptions.IdempotencyLevel.NO_SIDE_EFFECTS
IDEMPOTENCY_UNKNOWN = MethodOptions.IdempotencyLevel.IDEMPOTENCY_UNKNOWN

# name, request, response, a read (NO_SIDE_EFFECTS: Connect sends it as an HTTP GET)
RPCS = [
    ("CreateSimulation", "sincero.SimulationInput", "sincero.CreateSimulationResponse", False),
    ("GetSimulation", "sincero.GetSimulationRequest", "sincero.Simulation", True),
    ("GetComparison", "sincero.GetComparisonRequest", "sincero.Comparison", True),
    ("CreateComparison", "sincero.CreateComparisonRequest", "sincero.Comparison", False),
    ("CreateWhatIf", "sincero.CreateWhatIfRequest", "sincero.Comparison", False),
    ("CreateCashLadder", "sincero.CreateCashLadderRequest", "sincero.Comparison", False),
    ("ListFields", "sincero.ListFieldsRequest", "sincero.ListFieldsResponse", True),
]


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def camel(name: str) -> str:
    return name[0].lower() + name[1:]


# ----- the service ------------------------------------------------------------------------------
def test_one_service_sincero_simulations():
    assert [svc.type_name for svc in SERVICE.file.services] == ["sincero.Simulations"]


def test_the_rpcs_their_types_and_which_are_reads():
    actual = [(m.name, m.input.type_name, m.output.type_name, m.idempotency == NO_SIDE_EFFECTS)
              for m in SERVICE.methods]
    assert actual == RPCS


def test_every_rpc_is_unary():
    assert {m.method_kind for m in SERVICE.methods} == {"unary"}


def test_the_writes_are_not_marked_idempotent():
    """Only reads are GETs; a write is a POST even though the content-addressed ids make it safe to retry."""
    writes = [m for m in SERVICE.methods if m.name.startswith("Create")]
    assert len(writes) == 4 and all(m.idempotency == IDEMPOTENCY_UNKNOWN for m in writes)


@pytest.mark.parametrize("cls", [connect.Simulations, connect.SimulationsSync,
                                 connect.SimulationsClient, connect.SimulationsClientSync])
def test_the_server_protocols_and_the_clients_have_every_rpc(cls):
    for name, *_ in RPCS:
        assert callable(getattr(cls, snake(name), None)), f"{cls.__name__}.{snake(name)}"


def test_the_asgi_and_wsgi_apps_serve_the_service_path():
    class Impl(connect.Simulations):
        pass

    class ImplSync(connect.SimulationsSync):
        pass

    assert connect.SimulationsASGIApplication(Impl()).path == "/sincero.Simulations"
    assert connect.SimulationsWSGIApplication(ImplSync()).path == "/sincero.Simulations"


def test_the_typescript_descriptor_has_the_same_rpcs():
    ts = (TARGETS["typescript"].out / "sincero" / "simulations_service_pb.ts")
    if not ts.exists():
        pytest.skip("frontend/src/gen not generated")
    block = ts.read_text(encoding="utf-8").split("export const Simulations: GenService<{", 1)[1]
    found = re.findall(r"(\w+): \{\s*methodKind: \"(\w+)\";\s*input: typeof (\w+)Schema;\s*output: typeof (\w+)Schema;", block)
    assert found == [(camel(n), "unary", req.split(".")[1], resp.split(".")[1]) for n, req, resp, _ in RPCS]


def test_every_id_in_a_request_must_not_be_empty():
    ids = [(m.name, f) for m in SERVICE.methods for f in m.input.fields if f.name in ("id", "ids", "relative_to")]
    assert len(ids) == 5
    for rpc, field in ids:
        rules = json.loads(field.proto.options[rules_ext].to_json())
        string_rules = rules["repeated"]["items"]["string"] if "repeated" in rules else rules["string"]
        assert string_rules == {"minLen": "1"}, f"{rpc}.{field.name}"


# ----- the result messages mirror the JSON view ---------------------------------------------------
RA = SimulationInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500,
                                  balloon_months=(6, 12)))
NULLS = SimulationInput(ContractData("N", 300_000, 24), bank_credit=BankCreditData(pre_approved_credit=None))


def assert_same(view, message_json, path="$"):
    """Every key of the view is in the message with the same value, and nothing else is.
    A `None` of the view is an unset field (absent from the message's JSON)."""
    if isinstance(view, dict):
        present = {k for k, v in view.items() if v is not None}
        assert set(message_json) == present, f"{path}: {sorted(set(message_json) ^ present)}"
        for key in present:
            assert_same(view[key], message_json[key], f"{path}.{key}")
    elif isinstance(view, list):
        assert len(view) == len(message_json), path
        for i, (a, b) in enumerate(zip(view, message_json)):
            assert_same(a, b, f"{path}[{i}]")
    elif isinstance(view, float) or isinstance(message_json, float):
        assert math.isclose(view, message_json, rel_tol=0, abs_tol=0), f"{path}: {view} != {message_json}"
    else:
        assert view == message_json, f"{path}: {view!r} != {message_json!r}"


def round_trip(cls, view: dict) -> dict:
    """The view's dict through the message: unknown keys refuse to parse; every field is emitted."""
    message = cls.from_json(json.dumps(view))
    return json.loads(message.to_json(use_proto_field_name=True, always_emit_implicit=True))


@pytest.mark.parametrize("inp", [RA, NULLS], ids=["RA", "nullable-unset"])
def test_simulation_result_is_simulation_to_dict_field_by_field(inp):
    view = simulation_to_dict(simulate(inp))
    assert_same(view, round_trip(SimulationResult, view))


@pytest.mark.parametrize("inp", [RA, NULLS], ids=["RA", "nullable-unset"])
def test_summary_is_summary_to_dict_field_by_field(inp):
    view = summary_to_dict(simulate(inp))
    assert_same(view, round_trip(Summary, view))


def test_the_sections_are_the_view_keys_in_order():
    view = simulation_to_dict(simulate(RA))
    assert [f.name for f in SimulationResult.desc().fields] == [
        "input", "rates", "down_payment", "mortgage", "construction_interest", "closing_costs",
        "financing", "credit_gap", "total_cost", "timeline"]
    assert set(view) == {f.name for f in SimulationResult.desc().fields}
    assert [f.name for f in Summary.desc().fields] == list(summary_to_dict(simulate(RA)))
