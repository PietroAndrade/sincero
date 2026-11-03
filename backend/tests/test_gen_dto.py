"""
The input fields come from `proto/sincero/simulation_input.proto`: the generated module is
up to date, the DTOs are built on it, and the generator enforces the .proto's conventions.
"""
import uuid
from dataclasses import fields
from pathlib import Path

import pytest

from app.models import BankCreditData, ContractData, MarketData, field_defaults, field_names
from app.models.input_dto import INPUT_GROUPS
from app.models import input_fields
from tools import gen_dto
from tools.gen_dto import PROTO, PROTO_DIR, TARGET, GeneratorError, compile_proto, read_groups, render


@pytest.fixture(scope="module")
def groups():
    return read_groups(compile_proto(PROTO, [PROTO_DIR]), PROTO)


# ----- the generated module and the .proto agree ---------------------------------------------
def test_generated_module_is_up_to_date():
    assert TARGET.read_text(encoding="utf-8") == render(), "app/models/input_fields.py is stale: run `make dto`"


def test_check_mode_passes_on_the_committed_file(capsys):
    assert gen_dto.main(["--check"]) == 0
    assert capsys.readouterr().out == ""


def test_proto_declares_every_input_field_in_dto_order(groups):
    proto_fields = [f.name for g in groups for f in g.fields]
    assert proto_fields == list(field_names())
    assert [g.name for g in groups] == ["CONTRACT", "MARKET", "BANK_CREDIT"]


def test_dtos_subclass_the_generated_fields_and_add_nothing_but_behaviour(groups):
    assert INPUT_GROUPS == (ContractData, MarketData, BankCreditData)
    for dto, group in zip(INPUT_GROUPS, groups):
        base = getattr(input_fields, group.class_name)
        assert dto.__bases__ == (base,)
        assert [f.name for f in fields(dto)] == [f.name for f in fields(base)] == [f.name for f in group.fields]
        assert not dto.__dataclass_fields__.keys() - base.__dataclass_fields__.keys()


def test_defaults_and_nullability_come_from_the_proto(groups):
    by_name = {f.name: f for g in groups for f in g.fields}
    assert by_name["list_price"].default is None and by_name["months_remaining"].default is None
    assert by_name["name"].default is None                                   # required by the model
    assert by_name["developer_installment"].annotation == "Optional[float]"
    assert by_name["pre_approved_credit"].annotation == "Optional[float]"
    assert by_name["balloon_months"].annotation == "tuple[int, ...]"
    assert field_defaults() == {"down_payment_pct": 20.0, "fgts_upfront": 0.0, "cash_upfront": 0.0,
                                "developer_installment": None, "incc_rate_pa": 7.0, "bank_rate_pa": 10.26,
                                "term_months": 360, "itbi_pct": 2.0, "registry_pct": 0.5,
                                "income_commitment_ratio": 0.3, "pre_approved_credit": None, "pro_soluto_months": 12}


# ----- the generator's rules, on throw-away protos -------------------------------------------
def render_proto(tmp_path: Path, body: str, message: str = "Input") -> str:
    """Compile a one-message proto that uses `(sincero.field)` and render it."""
    name = f"case_{uuid.uuid4().hex[:8]}"     # the process-wide descriptor pool refuses a file or a symbol twice
    preamble = f'''syntax = "proto3";
package sincero.{name};
import "sincero/simulation_input.proto";
'''
    (tmp_path / "cases").mkdir(exist_ok=True)
    (tmp_path / "cases" / f"{name}.proto").write_text(preamble + body)
    proto = f"cases/{name}.proto"
    return render(proto, [tmp_path, PROTO_DIR], message)


def test_each_field_shape_maps_to_its_dataclass_field(tmp_path):
    source = render_proto(tmp_path, '''
message Input {
  // A label.
  string label = 1 [(sincero.field) = {group: CONTRACT}];
  int32 count = 2 [(sincero.field) = {group: CONTRACT}];
  optional double ratio = 3 [(sincero.field) = {group: CONTRACT default_number: 0.25}];
  optional int32 months = 4 [(sincero.field) = {group: MARKET default_integer: 12}];
  optional string kind = 5 [(sincero.field) = {group: MARKET default_string: "SAC"}];
  optional double limit = 6 [(sincero.field) = {group: BANK_CREDIT nullable: true}];
  repeated int32 items = 7 [(sincero.field) = {group: BANK_CREDIT}];
}
''')
    assert "DO NOT EDIT" in source
    assert '''@dataclass(frozen=True)
class ContractFields:
    """The contract with the developer: the property, the down payment and how it is paid."""

    # A label.
    label: str
    count: int
    ratio: float = 0.25


@dataclass(frozen=True)
class MarketFields:
    """Market and regulatory conditions, independent of the property."""

    months: int = 12
    kind: str = 'SAC'


@dataclass(frozen=True)
class BankCreditFields:
    """The bank's position at signing and the fallback when it falls short at delivery."""

    limit: Optional[float] = None
    items: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self):
        object.__setattr__(self, "items", tuple(self.items))
''' in source
    namespace: dict = {}
    exec(compile(source, "generated", "exec"), namespace)   # the generated module is valid Python
    assert namespace["BankCreditFields"](items=[3, 1]).items == (3, 1)


def one_of_each_group(middle: str) -> str:
    """A message with one field per group, so that every group is populated, plus `middle`."""
    return f'''
message Input {{
  double a = 1 [(sincero.field) = {{group: CONTRACT}}];
  {middle}
  optional double m = 98 [(sincero.field) = {{group: MARKET default_number: 1}}];
  optional double b = 99 [(sincero.field) = {{group: BANK_CREDIT default_number: 1}}];
}}
'''


@pytest.mark.parametrize("field_line, error", [
    ('double x = 2;', "x: missing the (sincero.field) option"),
    ('double x = 2 [(sincero.field) = {nullable: true}];', "x: group is unspecified"),
    ('optional double x = 2 [(sincero.field) = {group: CONTRACT}];', "x: optional, but neither a default nor nullable"),
    ('optional double x = 2 [(sincero.field) = {group: CONTRACT default_number: 1 nullable: true}];',
     "x: either a default or nullable, not both"),
    ('optional double x = 2 [(sincero.field) = {group: CONTRACT default_integer: 1}];',
     "x: default_integer does not match the field's type (expected default_number)"),
    ('optional int32 x = 2 [(sincero.field) = {group: CONTRACT default_string: "1"}];',
     "x: default_string does not match the field's type (expected default_integer)"),
    ('double x = 2 [(sincero.field) = {group: CONTRACT default_number: 1}];',
     "x: a required field cannot have a default or be nullable; mark it optional"),
    ('double x = 2 [(sincero.field) = {group: CONTRACT nullable: true}];',
     "x: a required field cannot have a default or be nullable"),
    ('repeated int32 x = 2 [(sincero.field) = {group: CONTRACT default_integer: 1}];',
     "x: a repeated field is always a tuple, empty by default"),
    ('bool x = 2 [(sincero.field) = {group: CONTRACT}];', "x: unsupported type TYPE_BOOL"),
    ('optional double x = 2 [(sincero.field) = {group: CONTRACT default_number: 1}];\n  double y = 3 [(sincero.field) = {group: CONTRACT}];',
     "y: required field after an optional one in group CONTRACT"),
], ids=lambda s: s.split(":")[0] if ":" in s and not s.endswith(";") else None)
def test_generator_refuses_a_field_that_breaks_the_conventions(tmp_path, field_line, error):
    with pytest.raises(GeneratorError, match=error.replace("(", r"\(").replace(")", r"\)")):
        render_proto(tmp_path, one_of_each_group(field_line))


def test_generator_refuses_an_empty_group(tmp_path):
    with pytest.raises(GeneratorError, match="Group.BANK_CREDIT: no field belongs to it"):
        render_proto(tmp_path, '''
message Input {
  double a = 1 [(sincero.field) = {group: CONTRACT}];
  double m = 2 [(sincero.field) = {group: MARKET}];
}
''')


def test_generator_refuses_a_proto_that_does_not_compile(tmp_path):
    with pytest.raises(GeneratorError, match="protoc failed"):
        render_proto(tmp_path, "message Input { double a = 1 [(sincero.field) = {group: NOWHERE}]; }")
