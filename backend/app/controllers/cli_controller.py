"""
Command-line controller.

    python cli.py                                   # the five reference properties
    python cli.py --price 440000 --months 19 --fgts 13000 --installment 2500 --balloon-month 6 --balloon-month 12
                                 (--months = months REMAINING until delivery)
    python cli.py --price 440000 --months 19 --cash-ladder 0,30000,100000
    python cli.py --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35
    python cli.py --price 440000 --months 19 --json  # full JSON payload (same shape as the API)
"""
from __future__ import annotations

import argparse
import json

from app.models import ContractData, SimulationError, SimulationInput, cash_ladder, compare, field_defaults, simulate
from app.views import comparison_table, report, simulation_to_dict, what_if_to_dict
from app.views.text_view import brl

REFERENCE_PROPERTIES = [("SO", 300_000, 4), ("F", 396_000, 8), ("SV", 233_000, 17),
                        ("F4", 320_400, 19), ("RA", 440_000, 19)]


# CLI flag -> input field (of ContractData, MarketData or BankCreditData). Defaults are NOT
# repeated here: they come from the model DTOs (single source of truth) and are shown in --help.
FLAG_FIELDS = {
    "--name": "name",
    "--price": "list_price",
    "--months": "months_remaining",
    "--down-payment-pct": "down_payment_pct",
    "--fgts": "fgts_upfront",
    "--cash": "cash_upfront",
    "--installment": "developer_installment",
    "--balloon-month": "balloon_months",
    "--incc": "incc_rate_pa",
    "--bank-rate": "bank_rate_pa",
    "--term": "term_months",
    "--itbi": "itbi_pct",
    "--registry": "registry_pct",
    "--income-ratio": "income_commitment_ratio",
    "--pre-approved": "pre_approved_credit",
    "--pro-soluto-months": "pro_soluto_months",
}

HELP = {
    "name": "label of the property (default: %(default)s)",
    "list_price": "list price in R$",
    "months_remaining": "months remaining until delivery (time left, not the project's total duration)",
    "down_payment_pct": "down payment required by the developer, %% of the list price (default: %(default)s)",
    "fgts_upfront": "FGTS used at signing, R$ (default: %(default)s)",
    "cash_upfront": "cash paid at signing, R$; above the down payment it reduces the financed balance (default: %(default)s)",
    "developer_installment": "monthly amount paid to the developer; what it does not cover becomes balloons "
                             "(default: balance / months)",
    "balloon_months": "construction month with a balloon payment (repeatable); the amount is derived",
    "incc_rate_pa": "INCC, %% per year (default: %(default)s)",
    "bank_rate_pa": "bank interest rate, %% per year (default: %(default)s)",
    "term_months": "bank financing term in months (default: %(default)s)",
    "itbi_pct": "ITBI, %% of the list price (default: %(default)s)",
    "registry_pct": "registry and deed costs, %% of the list price (default: %(default)s)",
    "income_commitment_ratio": "max share of household income the bank accepts as installment, 0-1 (default: %(default)s)",
    "pre_approved_credit": "credit pre-approved by the bank at signing, R$ (default: nominal mortgage balance)",
    "pro_soluto_months": "months to pay the developer any credit gap (default: %(default)s)",
}

_TYPES = {"name": str, "months_remaining": int, "term_months": int, "pro_soluto_months": int}


def model_defaults() -> dict:
    """Default of every input field that has one (read from the model DTOs)."""
    return field_defaults()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="SINCERO — off-plan apartment cost simulator (Brazil)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    defaults = {**model_defaults(), "name": "CUSTOM"}  # `name` is the only field without a model default
    for flag, field in FLAG_FIELDS.items():
        metavar = flag.lstrip("-").upper().replace("-", "_")
        if field == "balloon_months":
            ap.add_argument(flag, dest=field, type=int, action="append", default=[], metavar=metavar, help=HELP[field])
            continue
        ap.add_argument(flag, dest=field, type=_TYPES.get(field, float), default=defaults.get(field),
                        metavar=metavar, help=HELP[field])
    ap.add_argument("--cash-ladder", help="comma-separated cash amounts to compare, e.g. 0,30000,100000")
    ap.add_argument("--json", action="store_true", help="print the JSON payload instead of the text report")
    return ap


def input_from_args(args: argparse.Namespace) -> SimulationInput:
    data = {field: getattr(args, field) for field in FLAG_FIELDS.values()}
    data["balloon_months"] = tuple(data["balloon_months"])
    return SimulationInput.from_dict(data)


def run_reference() -> str:
    inputs = [SimulationInput(ContractData(n, p, m, fgts_upfront=13_000)) for n, p, m in REFERENCE_PROPERTIES]
    results = compare(inputs)
    parts = ["=== REFERENCE PROPERTIES: 20% down payment, R$ 13,000 FGTS upfront ===", "",
             comparison_table(results), ""]
    parts += [report(r) + "\n" for r in results]
    return "\n".join(parts)


def run_cash_ladder(inp: SimulationInput, amounts: list[float], as_json: bool) -> str:
    ladder = what_if_to_dict(cash_ladder(inp, amounts))
    if as_json:
        return json.dumps(ladder, indent=2)
    header = f"{'Cash upfront':>14}{'Dev/mo':>13}{'Hidden INCC':>14}{'Balance@deliv':>16}{'SAC 1st':>12}{'Min income':>14}"
    rows = [f"{brl(s['summary']['cash_upfront']):>14}{brl(s['summary']['developer_installment']):>13}"
            f"{brl(s['summary']['hidden_incc_debt']):>14}{brl(s['summary']['balance_at_delivery']):>16}"
            f"{brl(s['summary']['sac_first_installment']):>12}{brl(s['summary']['min_income_sac']):>14}"
            for s in ladder["scenarios"]]
    return "\n".join([header, *rows])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_price is None:
        print(run_reference())
        return 0
    try:
        inp = input_from_args(args)
        if args.cash_ladder:
            print(run_cash_ladder(inp, [float(a) for a in args.cash_ladder.split(",")], args.json))
        else:
            result = simulate(inp)
            print(json.dumps(simulation_to_dict(result), indent=2) if args.json else report(result))
    except SimulationError as exc:
        print(f"error: {exc}")
        return 2
    return 0
