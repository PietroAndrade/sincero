"""The CLI exposes every model input and never re-declares the model's defaults."""
import pytest

from app.controllers.cli_controller import FLAG_FIELDS, build_parser, input_from_args, main
from app.models import ContractData, SimulationInput, field_names


def test_every_model_field_has_a_cli_flag():
    model_fields = set(field_names())
    assert set(FLAG_FIELDS.values()) == model_fields, (
        f"fields without a flag: {model_fields - set(FLAG_FIELDS.values())}; "
        f"flags without a field: {set(FLAG_FIELDS.values()) - model_fields}")


def test_cli_defaults_are_the_model_defaults():
    args = build_parser().parse_args(["--price", "440000", "--months", "19"])
    inp = input_from_args(args)
    assert inp == SimulationInput(ContractData("CUSTOM", 440_000, 19))


def test_closing_costs_income_ratio_and_pro_soluto_flags_reach_the_model():
    args = build_parser().parse_args(["--price", "440000", "--months", "19", "--itbi", "3", "--registry", "1",
                                      "--income-ratio", "0.35", "--pro-soluto-months", "24",
                                      "--balloon-month", "6", "--balloon-month", "12", "--installment", "2500"])
    inp = input_from_args(args)
    market, credit, contract = inp.market(), inp.bank_credit(), inp.contract()
    assert (market.itbi_pct, market.registry_pct, market.income_commitment_ratio, credit.pro_soluto_months) == (3, 1, 0.35, 24)
    assert contract.balloon_months == (6, 12) and contract.developer_installment == 2500


def test_help_shows_model_defaults_once(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    assert "(default: 7.0)" in out and "(default: 0.5)" in out and "(default: 0.3)" in out


def test_invalid_input_exits_with_code_2(capsys):
    assert main(["--price", "440000", "--months", "0"]) == 2
    assert "months remaining until delivery must be at least 1" in capsys.readouterr().out
