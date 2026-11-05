"""
`protovalidate` on the real `SimulationInput` message: `list_price` and `months_remaining` have
explicit presence, so "absent" and "zero" are different violations
(docs/decisions/required-fields-explicit-presence.md).
"""
import json

import pytest

protovalidate = pytest.importorskip("protovalidate")
from google.protobuf import descriptor_pool, json_format, message_factory  # noqa: E402

from tools.gen_dto import MESSAGE, PROTO, PROTO_DIR, compile_proto  # noqa: E402


@pytest.fixture(scope="module")
def message_class():
    compile_proto(PROTO, [PROTO_DIR])
    return message_factory.GetMessageClass(descriptor_pool.Default().FindMessageTypeByName(f"sincero.{MESSAGE}"))


def violations(message_class, body: dict) -> set[tuple[str, str]]:
    message = json_format.Parse(json.dumps(body), message_class())
    try:
        protovalidate.validate(message)
    except protovalidate.ValidationError as exc:
        return {(v.proto.field.elements[0].field_name, v.proto.rule_id) for v in exc.violations}
    return set()


@pytest.mark.parametrize("body, expected", [
    ({}, {("list_price", "required"), ("months_remaining", "required")}),
    ({"list_price": None, "months_remaining": 19}, {("list_price", "required")}),
    ({"list_price": 440000, "months_remaining": None}, {("months_remaining", "required")}),
    ({"list_price": 0, "months_remaining": 19}, {("list_price", "double.gt")}),
    ({"list_price": 440000, "months_remaining": 0}, {("months_remaining", "int32.gte_lte")}),
    ({"list_price": 440000, "months_remaining": 601}, {("months_remaining", "int32.gte_lte")}),
    ({"list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000}, set()),
])
def test_presence_and_range_violations(message_class, body, expected):
    assert violations(message_class, body) == expected


def test_zero_and_absent_are_different_violations(message_class):
    absent = violations(message_class, {"months_remaining": 19})
    zero = violations(message_class, {"list_price": 0, "months_remaining": 19})
    assert absent != zero and absent == {("list_price", "required")}
