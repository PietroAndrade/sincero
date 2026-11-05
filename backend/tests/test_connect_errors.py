"""
The errors of the Connect service (app/controllers/connect_errors.py, docs/api-contract.md
"Errors"): a `SimulationError` is `invalid_argument` + `ErrorInfo` (reason `invalid_input`, the
model's message verbatim, the item's `index`); a `buf.validate` rule is `invalid_argument` +
`BadRequest`; an unknown id is `not_found`. Then the same errors on the wire, through the
generated ASGI application built by `connect_app.asgi_app`, as a Connect client receives them.
"""
import asyncio
import base64
import json

import pytest

pytest.importorskip("connectrpc")
from connectrpc.code import Code  # noqa: E402
from connectrpc.errors import ConnectError  # noqa: E402

from app.controllers import connect_errors as errors  # noqa: E402
from app.controllers.connect_app import asgi_app  # noqa: E402
from app.gen.google.rpc.error_details_pb import BadRequest, ErrorInfo  # noqa: E402
from app.gen.sincero import simulations_service_connect as connect  # noqa: E402
from app.gen.sincero import simulations_service_pb as pb  # noqa: E402
from app.gen.sincero.simulation_input_pb import SimulationInput, SimulationOverrides  # noqa: E402
from app.models import SimulationError, simulate  # noqa: E402
from app.models import SimulationInput as ModelInput  # noqa: E402
from app.models.input_dto import ContractData  # noqa: E402

RA = ModelInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000))


def model_message(inp: ModelInput) -> str:
    with pytest.raises(SimulationError) as exc:
        simulate(inp)
    return str(exc.value)


def only_detail(err: ConnectError, cls):
    assert len(err.details) == 1 and err.details[0].type_name == cls.desc().type_name
    return cls.from_binary(err.details[0].message_bytes)         # as a client decodes it


# ----- SimulationError -> invalid_argument + ErrorInfo --------------------------------------------
IMPOSSIBLE = [
    ModelInput(ContractData("P0", 0, 19)),
    ModelInput(ContractData("M0", 440_000, 0)),
    ModelInput(ContractData("UP", 440_000, 19, fgts_upfront=500_000)),
    ModelInput(ContractData("BL", 440_000, 19, developer_installment=2_500, balloon_months=(25,))),
    ModelInput(ContractData("NI", 440_000, 19, balloon_months=(6,))),
]


@pytest.mark.parametrize("inp", IMPOSSIBLE, ids=lambda i: i.contract.name)
def test_a_model_rule_is_invalid_argument_with_the_message_verbatim_and_an_error_info(inp):
    with pytest.raises(ConnectError) as exc:
        errors.simulate_one(inp)
    err = exc.value
    assert err.code == Code.INVALID_ARGUMENT
    assert err.message == model_message(inp)
    info = only_detail(err, ErrorInfo)
    assert (info.reason, info.domain, dict(info.metadata)) == ("invalid_input", "sincero", {})
    assert isinstance(err.__cause__, SimulationError)


def test_simulate_one_returns_the_result_when_the_model_accepts_the_input():
    assert errors.simulate_one(RA).total_cost.total == simulate(RA).total_cost.total


def test_simulate_all_names_the_first_failing_item_and_returns_nothing():
    inputs = [RA, IMPOSSIBLE[2], IMPOSSIBLE[0]]
    with pytest.raises(ConnectError) as exc:
        errors.simulate_all(inputs)
    info = only_detail(exc.value, ErrorInfo)
    assert dict(info.metadata) == {"index": "1"}
    assert exc.value.message == model_message(IMPOSSIBLE[2])


def test_simulate_all_returns_every_result_in_order():
    second = ModelInput(ContractData("RB", 300_000, 24))
    assert [r.input.contract.name for r in errors.simulate_all([RA, second])] == ["RA", "RB"]


# ----- buf.validate -> invalid_argument + BadRequest ------------------------------------------------
@pytest.mark.parametrize("request_, violations", [
    (SimulationInput(list_price=440000),
     [("months_remaining", "required", "value is required")]),
    (SimulationInput(),
     [("list_price", "required", "value is required"), ("months_remaining", "required", "value is required")]),
    (pb.CreateWhatIfRequest(id="56c8", variations=[SimulationOverrides(cash_upfront=1), SimulationOverrides(months_remaining=0)]),
     [("variations[1].months_remaining", "int32.gte_lte", "must be greater than or equal to 1 and less than or equal to 600")]),
    (pb.CreateComparisonRequest(candidates=[SimulationOverrides(months_remaining=19)]),
     [("", "candidates.list_price", "every candidate needs list_price, its own or base's")]),
    (pb.CreateCashLadderRequest(id="56c8", amounts=[0, -1]),
     [("amounts[1]", "double.gte_lte", "must be greater than or equal to 0 and less than or equal to 1000000000000")]),
])
def test_a_proto_rule_is_invalid_argument_with_one_field_violation_per_rule(request_, violations):
    with pytest.raises(ConnectError) as exc:
        errors.validate(request_)
    assert exc.value.code == Code.INVALID_ARGUMENT
    bad = only_detail(exc.value, BadRequest)
    assert [(v.field, v.reason, v.description) for v in bad.field_violations] == violations
    assert exc.value.message == "; ".join(f"{f}: {d}" if f else d for f, _, d in violations)


def test_a_valid_request_passes():
    errors.validate(SimulationInput(list_price=440000, months_remaining=19))
    errors.validate(pb.CreateWhatIfRequest(id="56c8", variations=[SimulationOverrides(incc_rate_pa=4.0)]))


def test_an_unknown_id_is_not_found():
    err = errors.not_found("deadbeef")
    assert (err.code, err.message, err.details) == (Code.NOT_FOUND, "simulation not found: deadbeef", [])


# ----- on the wire -------------------------------------------------------------------------------------
class Service(connect.Simulations):
    """Just enough of the service to raise each error the way the real one will."""

    async def create_simulation(self, request, ctx):
        errors.validate(request)
        contract = ContractData(request.name or "CUSTOM", request.list_price, request.months_remaining,
                                fgts_upfront=request.fgts_upfront if request.has_field("fgts_upfront") else 0.0)
        errors.simulate_one(ModelInput(contract))
        return pb.CreateSimulationResponse(id="56c8")

    async def get_simulation(self, request, ctx):
        errors.validate(request)
        raise errors.not_found(request.id)


def post(rpc: str, body: bytes) -> tuple[int, dict]:
    """One Connect+JSON unary call into the ASGI app, in-process."""
    path = f"/sincero.Simulations/{rpc}"
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
             "server": ("test", 80), "client": ("test", 1)}
    inbox = [{"type": "http.request", "body": body, "more_body": False}]
    status, chunks = [], []

    async def receive():
        return inbox.pop(0) if inbox else {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            status.append(message["status"])
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    asyncio.run(asgi_app(Service())(scope, receive, send))
    return status[0], json.loads(b"".join(chunks))


def wire_detail(body: dict, cls):
    [detail] = body["details"]
    assert detail["type"] == cls.desc().type_name
    value = detail["value"]
    return cls.from_binary(base64.b64decode(value + "=" * (-len(value) % 4)))


def test_wire_a_model_rule():
    status, body = post("CreateSimulation", b'{"list_price": 440000, "months_remaining": 19, "fgts_upfront": 500000}')
    assert (status, body["code"]) == (400, "invalid_argument")
    assert body["message"] == model_message(ModelInput(ContractData("X", 440_000, 19, fgts_upfront=500_000)))
    info = wire_detail(body, ErrorInfo)
    assert (info.reason, info.domain) == ("invalid_input", "sincero")


def test_wire_a_proto_rule():
    status, body = post("CreateSimulation", b'{"listPrice": "440000"}')     # camelCase and a string: the JSON mapping
    assert (status, body["code"], body["message"]) == (400, "invalid_argument", "months_remaining: value is required")
    [violation] = wire_detail(body, BadRequest).field_violations
    assert (violation.field, violation.reason) == ("months_remaining", "required")


def test_wire_an_unknown_key_is_refused():
    status, body = post("CreateSimulation", b'{"list_price": 440000, "months_remaining": 19, "list_prise": 1}')
    assert (status, body["code"]) == (400, "invalid_argument")
    assert "list_prise" in body["message"] and "details" not in body


def test_wire_not_found():
    status, body = post("GetSimulation", b'{"id": "deadbeef"}')
    assert (status, body) == (404, {"code": "not_found", "message": "simulation not found: deadbeef"})


def test_wire_success():
    assert post("CreateSimulation", b'{"list_price": 440000, "months_remaining": 19}') == (200, {"id": "56c8"})
