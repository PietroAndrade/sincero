"""The input contract (pure interface), the input DTOs and the small validators behind SimulationInput.validate()."""
import inspect
from dataclasses import FrozenInstanceError, fields

import pytest

from app.models import (BankCreditData, CompositeValidator, ContractData, InputValidator, MarketData,
                        SimulationError, SimulationInput, SimulationInputInterface, default_validator,
                        field_defaults, field_names)
from app.models.input_dto import FIELD_OWNER, INPUT_GROUPS
from app.models.validators import (DEFAULT_VALIDATORS, BankCreditValidator, ClosingCostsValidator,
                                   DeveloperPlanValidator, FinancingValidator, MarketRatesValidator,
                                   PropertyValidator, UpfrontPaymentsValidator)


@pytest.fixture
def ra() -> SimulationInput:
    return SimulationInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500,
                                        balloon_months=(6, 12)))


# ----- the interface ---------------------------------------------------------
def test_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        SimulationInputInterface()  # type: ignore[abstract]


def test_interface_is_pure_only_abstract_methods_no_attributes():
    public = {name: member for name, member in vars(SimulationInputInterface).items()
              if not name.startswith("_")}
    assert public, "the interface declares nothing"
    for name, member in public.items():
        assert inspect.isfunction(member), f"{name} is not a method"
        assert getattr(member, "__isabstractmethod__", False), f"{name} is not abstract"
    assert not SimulationInputInterface.__dict__.get("__annotations__"), "the interface must not declare attributes"
    assert set(public) == SimulationInputInterface.__abstractmethods__ == {
        "contract", "market", "bank_credit",
        "required_down_payment", "upfront", "remaining_down_payment",
        "validate", "with_overrides"}


def test_simulation_input_implements_the_interface(ra):
    assert isinstance(ra, SimulationInputInterface)
    assert ra.contract().name == "RA" and ra.market() == MarketData() and ra.bank_credit() == BankCreditData()
    assert ra.required_down_payment() == pytest.approx(88_000)
    assert ra.upfront() == pytest.approx(13_000)
    assert ra.remaining_down_payment() == pytest.approx(75_000)
    assert ra.validate() is ra


def test_validator_base_is_abstract():
    with pytest.raises(TypeError):
        InputValidator()  # type: ignore[abstract]


# ----- the DTOs --------------------------------------------------------------
def test_dtos_are_frozen_and_hold_no_behaviour():
    for dto in INPUT_GROUPS:
        assert dto.__dataclass_params__.frozen
        methods = [n for n, m in vars(dto).items() if inspect.isfunction(m) and not n.startswith("_")]
        assert methods == [], f"{dto.__name__} has behaviour: {methods}"
    with pytest.raises(FrozenInstanceError):
        MarketData().incc_rate_pa = 1  # type: ignore[misc]


def test_dto_field_names_are_unique_and_routed():
    names = [f.name for dto in INPUT_GROUPS for f in fields(dto)]
    assert len(names) == len(set(names)) == 16
    assert field_names() == tuple(names)
    assert FIELD_OWNER["list_price"] is ContractData
    assert FIELD_OWNER["incc_rate_pa"] is MarketData
    assert FIELD_OWNER["pro_soluto_months"] is BankCreditData
    assert field_defaults()["incc_rate_pa"] == 7.0 and "list_price" not in field_defaults()


def test_contract_data_normalises_balloon_months_to_a_tuple():
    assert ContractData("X", 1, 1, balloon_months=[3, 1]).balloon_months == (3, 1)


# ----- composition: from_dict / to_dict / with_overrides -----------------------
def test_from_dict_routes_each_field_to_its_dto(ra):
    built = SimulationInput.from_dict({"name": "RA", "list_price": 440_000, "months_remaining": 19,
                                       "fgts_upfront": 13_000, "developer_installment": 2_500,
                                       "balloon_months": (6, 12), "incc_rate_pa": 7.0, "pro_soluto_months": 12})
    assert built == ra
    assert SimulationInput.from_dict(ra.to_dict()) == ra
    assert set(ra.to_dict()) == set(field_names())


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(TypeError, match="unknown simulation input field\\(s\\): colour, price"):
        SimulationInput.from_dict({"name": "X", "list_price": 1, "months_remaining": 1, "price": 1, "colour": "red"})


def test_with_overrides_crosses_dto_boundaries_and_keeps_the_original(ra):
    changed = ra.with_overrides(cash_upfront=30_000, incc_rate_pa=4.0, pro_soluto_months=24)
    assert (changed.contract().cash_upfront, changed.market().incc_rate_pa, changed.bank_credit().pro_soluto_months) \
        == (30_000, 4.0, 24)
    assert changed.contract().name == "RA" and changed.market().bank_rate_pa == 10.26
    assert (ra.contract().cash_upfront, ra.market().incc_rate_pa, ra.bank_credit().pro_soluto_months) == (0, 7.0, 12)
    with pytest.raises(TypeError):
        ra.with_overrides(nonsense=1)


def test_equality_and_hash_follow_the_dtos(ra):
    same = SimulationInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500,
                                        balloon_months=(6, 12)), MarketData(), BankCreditData())
    assert same == ra and hash(same) == hash(ra)
    assert ra.with_overrides(name="F") != ra
    assert "ContractData" in repr(ra) and "MarketData" in repr(ra)


# ----- each validator in isolation -------------------------------------------
@pytest.mark.parametrize("validator,overrides,message", [
    (PropertyValidator(), {"list_price": 0}, "list price must be greater than zero"),
    (PropertyValidator(), {"list_price": -1}, "list price must be greater than zero"),
    (PropertyValidator(), {"months_remaining": 0}, "months remaining until delivery must be at least 1"),
    (PropertyValidator(), {"down_payment_pct": -10}, "down payment percentage must be between 0 and 100"),
    (PropertyValidator(), {"down_payment_pct": 150}, "down payment percentage must be between 0 and 100"),
    (UpfrontPaymentsValidator(), {"fgts_upfront": -1}, "upfront payments must not be negative"),
    (UpfrontPaymentsValidator(), {"cash_upfront": -1}, "upfront payments must not be negative"),
    (UpfrontPaymentsValidator(), {"cash_upfront": 500_000},
     r"upfront payments of R\$ 513,000.00 exceed the list price of R\$ 440,000.00"),
    (UpfrontPaymentsValidator(), {"fgts_upfront": 300_000, "cash_upfront": 140_000.01},
     r"upfront payments of R\$ 440,000.01 exceed the list price"),
    (DeveloperPlanValidator(), {"developer_installment": -1}, "the monthly developer installment must not be negative"),
    (DeveloperPlanValidator(), {"balloon_months": (0,)}, "balloon month 0 must be at least 1"),
    (DeveloperPlanValidator(), {"balloon_months": (24,)}, r"balloon month 24 is after delivery \(month 19\)"),
    (DeveloperPlanValidator(), {"balloon_months": (6, 6)}, "balloon months must not repeat"),
    (MarketRatesValidator(), {"incc_rate_pa": -100}, "INCC rate must be greater than -100% per year"),
    (MarketRatesValidator(), {"incc_rate_pa": -250}, "INCC rate must be greater than -100% per year"),
    (MarketRatesValidator(), {"bank_rate_pa": -0.01}, "bank interest rate must not be negative"),
    (FinancingValidator(), {"term_months": 0}, "financing term must be at least 1 month"),
    (FinancingValidator(), {"income_commitment_ratio": 0}, "income commitment ratio must be between 0 and 1"),
    (FinancingValidator(), {"income_commitment_ratio": 1.5}, "income commitment ratio must be between 0 and 1"),
    (ClosingCostsValidator(), {"itbi_pct": -3}, "closing cost percentages must not be negative"),
    (ClosingCostsValidator(), {"registry_pct": -1}, "closing cost percentages must not be negative"),
    (BankCreditValidator(), {"pre_approved_credit": -1000}, "pre-approved credit must not be negative"),
    (BankCreditValidator(), {"pro_soluto_months": 0}, "pro-soluto term must be at least 1 month"),
])
def test_each_validator_rejects_its_own_field(ra, validator, overrides, message):
    with pytest.raises(SimulationError, match=message):
        validator.validate(ra.with_overrides(**overrides))


@pytest.mark.parametrize("validator", DEFAULT_VALIDATORS, ids=lambda v: type(v).__name__)
def test_each_validator_accepts_a_valid_contract(ra, validator):
    validator.validate(ra)  # must not raise


@pytest.mark.parametrize("overrides", [
    {"incc_rate_pa": -2.0},                 # deflation is a valid, if unusual, market
    {"incc_rate_pa": 0.0}, {"bank_rate_pa": 0.0},
    {"down_payment_pct": 0.0}, {"down_payment_pct": 100.0},
    {"pre_approved_credit": 0.0},
    {"fgts_upfront": 0.0, "cash_upfront": 440_000.0, "developer_installment": None, "balloon_months": ()},  # cash purchase
    {"developer_installment": 0.0, "balloon_months": (6,)},
    {"developer_installment": None, "balloon_months": ()},
])
def test_boundary_values_are_accepted(ra, overrides):
    ra.with_overrides(**overrides).validate()


def test_a_validator_only_reads_its_own_dto(ra):
    broken_market = ra.with_overrides(bank_rate_pa=-5)
    PropertyValidator().validate(broken_market)            # contract is fine; not its business
    with pytest.raises(SimulationError):
        MarketRatesValidator().validate(broken_market)


def test_validators_work_on_any_implementation_of_the_interface():
    class Stub(SimulationInputInterface):
        """A hand-rolled input: only the methods the validator needs are real."""
        def contract(self): return ContractData("stub", 100_000, 12, down_payment_pct=200)
        def market(self): return MarketData()
        def bank_credit(self): return BankCreditData()
        def required_down_payment(self): return 0.0
        def upfront(self): return 0.0
        def remaining_down_payment(self): return 0.0
        def validate(self): return self
        def with_overrides(self, **o): return self

    with pytest.raises(SimulationError, match="down payment percentage"):
        default_validator().validate(Stub())


# ----- composition -----------------------------------------------------------
def test_composite_runs_in_order_and_stops_at_the_first_error(ra):
    both_broken = ra.with_overrides(list_price=0, bank_rate_pa=-5)
    with pytest.raises(SimulationError, match="list price must be greater than zero"):
        default_validator().validate(both_broken)
    reversed_policy = CompositeValidator([MarketRatesValidator(), PropertyValidator()])
    with pytest.raises(SimulationError, match="bank interest rate must not be negative"):
        reversed_policy.validate(both_broken)


def test_default_policy_covers_every_validator():
    assert {type(v) for v in default_validator().validators} == {
        PropertyValidator, UpfrontPaymentsValidator, DeveloperPlanValidator, MarketRatesValidator,
        FinancingValidator, ClosingCostsValidator, BankCreditValidator}


def test_validate_accepts_a_custom_policy(ra):
    class Forbidding(InputValidator):
        def validate(self, inp):
            raise SimulationError("nope")

    with pytest.raises(SimulationError, match="nope"):
        ra.validate(Forbidding())
    assert ra.validate(CompositeValidator([])) is ra   # an empty policy accepts anything
