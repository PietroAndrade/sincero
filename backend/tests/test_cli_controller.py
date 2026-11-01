"""The CLI exposes every model input and never re-declares the model's defaults."""
from dataclasses import fields

import pytest

from app.controllers.cli_controller import FLAG_FIELDS, build_parser, input_from_args, main
from app.models import SimulationInput


def test_every_model_field_has_a_cli_flag():
    model_fields = {f.name for f in fields(SimulationInput)}
    assert set(FLAG_FIELDS.values()) == model_fields, (
        f"fields without a flag: {model_fields - set(FLAG_FIELDS.values())}; "
        f"flags without a field: {set(FLAG_FIELDS.values()) - model_fields}")


def test_cli_defaults_are_the_model_defaults():
    args = build_parser().parse_args(["--price", "440000", "--months", "19"])
    inp = input_from_args(args)
    assert inp == SimulationInput("CUSTOM", 440_000, 19)


def test_closing_costs_income_ratio_and_pro_soluto_flags_reach_the_model():
    args = build_parser().parse_args(["--price", "440000", "--months", "19", "--itbi", "3", "--registry", "1",
                                      "--income-ratio", "0.35", "--pro-soluto-months", "24",
                                      "--balloon-month", "6", "--balloon-month", "12", "--installment", "2500"])
    inp = input_from_args(args)
    assert (inp.itbi_pct, inp.registry_pct, inp.income_commitment_ratio, inp.pro_soluto_months) == (3, 1, 0.35, 24)
    assert inp.balloon_months == (6, 12) and inp.developer_installment == 2500


def test_help_shows_model_defaults_once(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--help"])
    out = capsys.readouterr().out
    assert "(default: 7.0)" in out and "(default: 0.5)" in out and "(default: 0.3)" in out


def test_invalid_input_exits_with_code_2(capsys):
    assert main(["--price", "440000", "--months", "0"]) == 2
    assert "months remaining until delivery must be at least 1" in capsys.readouterr().out
