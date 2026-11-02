"""The input DTOs, the behavioural interface, the composed SimulationInput and the small validators."""
import inspect
from dataclasses import FrozenInstanceError, fields, replace

import pytest

from app.models import (DEFAULT_POLICY, BankCreditData, CompositeValidator, ContractData, MarketData,
                        SimulationError, SimulationInput, SimulationInputInterface, ValidationPolicy, Validator,
                        field_defaults, field_names)
from app.models.input_dto import FIELD_OWNER, INPUT_GROUPS
from app.models.validators import (BankCreditValidator, ClosingCostsValidator, DeveloperPlanValidator,
                                   FinancingValidator, MarketRatesValidator, PropertyValidator,
                                   UpfrontPaymentsValidator)

# Baseline DTOs of the reference property "RA".
C = ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500, balloon_months=(6, 12))
M = MarketData()
B = BankCreditData()


@pytest.fixture
def ra() -> SimulationInput:
    return SimulationInput(C)


# ----- the DTOs --------------------------------------------------------------
def test_dtos_are_frozen_dataclasses():
    for dto in INPUT_GROUPS:
        assert dto.__dataclass_params__.frozen
    with pytest.raises(FrozenInstanceError):
        MarketData().incc_rate_pa = 1  # type: ignore[misc]


def test_only_the_contract_has_behaviour_and_only_about_its_own_amounts():
    def public_members(cls):
        return {n for n, m in vars(cls).items() if not n.startswith("_") and (inspect.isfunction(m) or isinstance(m, property))}
    assert public_members(MarketData) == public_members(BankCreditData) == set()
    assert public_members(ContractData) == {"required_down_payment", "upfront", "remaining_down_payment"}


def test_contract_derives_its_own_amounts():
    assert C.required_down_payment == pytest.approx(88_000)
    assert C.upfront == pytest.approx(13_000)
    assert C.remaining_down_payment == pytest.approx(75_000)
    assert replace(C, cash_upfront=100_000).remaining_down_payment == 0   # never negative


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


# ----- the interface ---------------------------------------------------------
def test_interface_is_pure_only_abstract_methods_no_attributes():
    with pytest.raises(TypeError):
        SimulationInputInterface()  # type: ignore[abstract]
    public = {n: m for n, m in vars(SimulationInputInterface).items() if not n.startswith("_")}
    assert all(inspect.isfunction(m) and m.__isabstractmethod__ for m in public.values())
    assert not SimulationInputInterface.__dict__.get("__annotations__")
    assert set(public) == SimulationInputInterface.__abstractmethods__ == {"validate", "with_overrides"}


def test_validator_base_is_abstract():
    with pytest.raises(TypeError):
        Validator()  # type: ignore[abstract]


# ----- SimulationInput: a frozen dataclass of three DTOs ----------------------
def test_simulation_input_is_a_frozen_dataclass_of_the_three_dtos(ra):
    assert isinstance(ra, SimulationInputInterface)
    assert SimulationInput.__dataclass_params__.frozen
    assert [f.name for f in fields(SimulationInput)] == ["contract", "market", "bank_credit"]
    assert ra.contract is C and ra.market == MarketData() and ra.bank_credit == BankCreditData()
    assert ra == SimulationInput(C, MarketData(), BankCreditData()) and hash(ra) == hash(SimulationInput(C))
    assert ra.validate() is ra


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
    assert (changed.contract.cash_upfront, changed.market.incc_rate_pa, changed.bank_credit.pro_soluto_months) \
        == (30_000, 4.0, 24)
    assert changed.contract.name == "RA" and changed.market.bank_rate_pa == 10.26
    assert (ra.contract.cash_upfront, ra.market.incc_rate_pa, ra.bank_credit.pro_soluto_months) == (0, 7.0, 12)
    assert ra.with_overrides(name="F") != ra
    with pytest.raises(TypeError):
        ra.with_overrides(nonsense=1)


# ----- each validator, in isolation, on the DTO it needs --------------------
@pytest.mark.parametrize("validator,data,message", [
    (PropertyValidator(), replace(C, list_price=0), "list price must be greater than zero"),
    (PropertyValidator(), replace(C, list_price=-1), "list price must be greater than zero"),
    (PropertyValidator(), replace(C, months_remaining=0), "months remaining until delivery must be at least 1"),
    (PropertyValidator(), replace(C, down_payment_pct=-10), "down payment percentage must be between 0 and 100"),
    (PropertyValidator(), replace(C, down_payment_pct=150), "down payment percentage must be between 0 and 100"),
    (UpfrontPaymentsValidator(), replace(C, fgts_upfront=-1), "upfront payments must not be negative"),
    (UpfrontPaymentsValidator(), replace(C, cash_upfront=-1), "upfront payments must not be negative"),
    (UpfrontPaymentsValidator(), replace(C, cash_upfront=500_000),
     r"upfront payments of R\$ 513,000.00 exceed the list price of R\$ 440,000.00"),
    (UpfrontPaymentsValidator(), replace(C, fgts_upfront=300_000, cash_upfront=140_000.01),
     r"upfront payments of R\$ 440,000.01 exceed the list price"),
    (DeveloperPlanValidator(), replace(C, developer_installment=-1), "the monthly developer installment must not be negative"),
    (DeveloperPlanValidator(), replace(C, balloon_months=(0,)), "balloon month 0 must be at least 1"),
    (DeveloperPlanValidator(), replace(C, balloon_months=(24,)), r"balloon month 24 is after delivery \(month 19\)"),
    (DeveloperPlanValidator(), replace(C, balloon_months=(6, 6)), "balloon months must not repeat"),
    (MarketRatesValidator(), replace(M, incc_rate_pa=-100), "INCC rate must be greater than -100% per year"),
    (MarketRatesValidator(), replace(M, incc_rate_pa=-250), "INCC rate must be greater than -100% per year"),
    (MarketRatesValidator(), replace(M, bank_rate_pa=-0.01), "bank interest rate must not be negative"),
    (FinancingValidator(), replace(M, term_months=0), "financing term must be at least 1 month"),
    (FinancingValidator(), replace(M, income_commitment_ratio=0), "income commitment ratio must be between 0 and 1"),
    (FinancingValidator(), replace(M, income_commitment_ratio=1.5), "income commitment ratio must be between 0 and 1"),
    (ClosingCostsValidator(), replace(M, itbi_pct=-3), "closing cost percentages must not be negative"),
    (ClosingCostsValidator(), replace(M, registry_pct=-1), "closing cost percentages must not be negative"),
    (BankCreditValidator(), replace(B, pre_approved_credit=-1000), "pre-approved credit must not be negative"),
    (BankCreditValidator(), replace(B, pro_soluto_months=0), "pro-soluto term must be at least 1 month"),
])
def test_each_validator_rejects_its_own_rule(validator, data, message):
    with pytest.raises(SimulationError, match=message):
        validator.validate(data)


@pytest.mark.parametrize("validator,data", [
    *[(v, C) for v in DEFAULT_POLICY.contract.validators],
    *[(v, M) for v in DEFAULT_POLICY.market.validators],
    *[(v, B) for v in DEFAULT_POLICY.bank_credit.validators],
], ids=lambda x: type(x).__name__)
def test_each_validator_accepts_valid_data(validator, data):
    validator.validate(data)  # must not raise


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


def test_validators_need_nothing_but_their_dto():
    """A market validator never sees the contract, so a broken contract cannot influence it."""
    MarketRatesValidator().validate(M)                       # no SimulationInput anywhere
    with pytest.raises(SimulationError):
        PropertyValidator().validate(replace(C, list_price=0))


# ----- composition -----------------------------------------------------------
def test_composite_runs_in_order_and_stops_at_the_first_error():
    both_broken = replace(C, list_price=0, cash_upfront=-1)
    with pytest.raises(SimulationError, match="list price must be greater than zero"):
        DEFAULT_POLICY.contract.validate(both_broken)
    reversed_order = CompositeValidator([UpfrontPaymentsValidator(), PropertyValidator()])
    with pytest.raises(SimulationError, match="upfront payments must not be negative"):
        reversed_order.validate(both_broken)


def test_default_policy_covers_every_validator_under_the_right_dto():
    assert {type(v) for v in DEFAULT_POLICY.contract.validators} == {
        PropertyValidator, UpfrontPaymentsValidator, DeveloperPlanValidator}
    assert {type(v) for v in DEFAULT_POLICY.market.validators} == {
        MarketRatesValidator, FinancingValidator, ClosingCostsValidator}
    assert {type(v) for v in DEFAULT_POLICY.bank_credit.validators} == {BankCreditValidator}


def test_policy_checks_contract_before_market_before_bank_credit(ra):
    everything_broken = ra.with_overrides(list_price=0, bank_rate_pa=-5, pro_soluto_months=0)
    with pytest.raises(SimulationError, match="list price"):
        everything_broken.validate()
    with pytest.raises(SimulationError, match="bank interest rate"):
        everything_broken.with_overrides(list_price=440_000).validate()
    with pytest.raises(SimulationError, match="pro-soluto"):
        everything_broken.with_overrides(list_price=440_000, bank_rate_pa=10.26).validate()


def test_validate_accepts_a_custom_policy(ra):
    class Forbidding(Validator):
        def validate(self, data):
            raise SimulationError("nope")

    accept_all = CompositeValidator([])
    with pytest.raises(SimulationError, match="nope"):
        ra.validate(ValidationPolicy(contract=accept_all, market=Forbidding(), bank_credit=accept_all))
    assert ra.validate(ValidationPolicy(accept_all, accept_all, accept_all)) is ra
