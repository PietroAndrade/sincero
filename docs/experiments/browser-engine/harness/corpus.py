"""
The inputs the engines are compared on, and what CPython answers for each (the reference).

    recorded   every simulate/compare call the behave suite makes (results/behave_calls.json,
               written by `run_features.py --engine cpython --record …`)
    reference  the five reference properties of the CLI, each simulated and cash-laddered
    random     seeded inputs over the whole input space: optional fields left out (defaults),
               nulls, balloons, zero rates (the `i == 0` branches), long terms, and one broken rule
               in ~1 case out of 8 (every `SimulationError`, plus unknown / missing fields) —
               including amounts ending in exactly half a cent, where Python and JavaScript
               round differently when the model formats its error message
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from browser import BACKEND, RESULTS, ROOT  # noqa: F401  (puts backend/ on sys.path)

import importlib.util

_spec = importlib.util.spec_from_file_location("sincero_bridge", ROOT / "web" / "sincero_bridge.py")
bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge)

REFERENCE = [("SO", 300_000, 4), ("F", 396_000, 8), ("SV", 233_000, 17), ("F4", 320_400, 19), ("RA", 440_000, 19)]
SEED = 20261108


def reference_cases() -> list[dict]:
    cases = []
    for name, price, months in REFERENCE:
        inp = {"name": name, "list_price": price, "months_remaining": months, "fgts_upfront": 13_000}
        cases.append({"kind": "simulate", "input": inp})
        cases.append({"kind": "cash_ladder", "input": inp, "amounts": [0, 30_000, 75_000, 100_000]})
    cases.append({"kind": "compare", "inputs": [c["input"] for c in cases if c["kind"] == "simulate"]})
    return cases


def _amount(r: random.Random, lo: float, hi: float) -> float:
    x = r.uniform(lo, hi)
    kind = r.random()
    if kind < 0.4:
        return round(x, 2)
    if kind < 0.6:
        return float(round(x / 1000) * 1000)
    if kind < 0.75:
        return int(x) + r.choice([0.125, 0.375, 0.625, 0.875])  # exact half-cent ties
    return x                                                    # full-precision doubles


def random_input(r: random.Random) -> dict:
    price = _amount(r, 120_000, 2_500_000)
    months = r.choice([r.randint(1, 60), r.randint(1, 24), 19])
    data: dict = {"name": f"R{r.randrange(10**6)}", "list_price": price, "months_remaining": months}
    opt = lambda p=0.6: r.random() < p  # noqa: E731  (set an optional field, or leave its default)
    if opt():
        data["down_payment_pct"] = r.choice([10.0, 20.0, 30.0, 0.0, 100.0, round(r.uniform(0, 60), 2)])
    if opt():
        data["fgts_upfront"] = r.choice([0.0, 13_000.0, _amount(r, 0, 90_000)])
    if opt(0.4):
        data["cash_upfront"] = _amount(r, 0, price * 0.5)
    pct = data.get("down_payment_pct", 20.0)
    remaining = max(0.0, price * pct / 100 - data.get("fgts_upfront", 0.0) - data.get("cash_upfront", 0.0))
    if opt(0.5):
        factor = r.choice([1.0, r.uniform(0.2, 0.99), r.uniform(0.2, 0.99), 0.0])
        data["developer_installment"] = round(remaining / months * factor, 2)
        if factor < 0.995 and r.random() < 0.9:
            data["balloon_months"] = r.sample(range(1, months + 1), k=r.randint(1, min(months, 6)))
    elif opt(0.1):
        data["developer_installment"] = None
    if opt():
        data["incc_rate_pa"] = r.choice([7.0, 0.0, round(r.uniform(-5, 15), 2), r.uniform(-20, 30)])
    if opt():
        data["bank_rate_pa"] = r.choice([10.26, 0.0, round(r.uniform(0, 16), 2)])
    if opt(0.4):
        data["term_months"] = r.choice([360, 420, 1, r.randint(1, 420)])
    if opt(0.3):
        data["itbi_pct"] = r.choice([2.0, 3.0, 0.0, round(r.uniform(0, 4), 2)])
    if opt(0.3):
        data["registry_pct"] = r.choice([0.5, 1.0, 0.0, round(r.uniform(0, 2), 2)])
    if opt(0.3):
        data["income_commitment_ratio"] = r.choice([0.3, 1.0, round(r.uniform(0.05, 1.0), 3)])
    if opt(0.4):
        data["pre_approved_credit"] = r.choice([None, 0.0, _amount(r, 0, price)])
    if opt(0.3):
        data["pro_soluto_months"] = r.choice([12, 1, r.randint(1, 60)])
    return data


BREAKERS = [
    lambda d, r: d.update(list_price=r.choice([0, -1.0, -440_000.125])),
    lambda d, r: d.update(months_remaining=r.choice([0, -3])),
    lambda d, r: d.update(down_payment_pct=r.choice([-0.5, 100.01, 250.0])),
    lambda d, r: d.update(fgts_upfront=-1.0),
    lambda d, r: d.update(cash_upfront=-0.01),
    lambda d, r: d.update(fgts_upfront=d["list_price"] * 0.7 + 0.125, cash_upfront=d["list_price"] * 0.5),
    lambda d, r: d.update(developer_installment=-10.0),
    lambda d, r: d.update(developer_installment=100.0, balloon_months=[d["months_remaining"] + r.randint(1, 5)]),
    lambda d, r: d.update(developer_installment=100.0, balloon_months=[0]),
    lambda d, r: d.update(developer_installment=10.0, balloon_months=[1, 1]) if d["months_remaining"] >= 1 else None,
    lambda d, r: d.update(developer_installment=None, balloon_months=[1]),
    lambda d, r: d.update(developer_installment=1_000_000.125, balloon_months=[]),   # exceeds the balance
    lambda d, r: d.update(developer_installment=0.125, balloon_months=[]),           # leaves a missing amount
    lambda d, r: d.update(incc_rate_pa=r.choice([-100.0, -250.0])),
    lambda d, r: d.update(bank_rate_pa=-0.1),
    lambda d, r: d.update(term_months=0),
    lambda d, r: d.update(income_commitment_ratio=r.choice([0.0, 1.5])),
    lambda d, r: d.update(itbi_pct=-1.0),
    lambda d, r: d.update(registry_pct=-0.5),
    lambda d, r: d.update(pre_approved_credit=-5.0),
    lambda d, r: d.update(pro_soluto_months=0),
    lambda d, r: d.update(list_prise=440_000),           # unknown field (TypeError)
    lambda d, r: d.pop("list_price"),                    # missing required field (TypeError)
]


def random_cases(n_simulate: int = 300, n_compare: int = 20, n_ladder: int = 20) -> list[dict]:
    r = random.Random(SEED)
    cases = []
    for _ in range(n_simulate):
        data = random_input(r)
        if r.random() < 0.125:
            BREAKERS[r.randrange(len(BREAKERS))](data, r)
        cases.append({"kind": "simulate", "input": data})
    for b in BREAKERS:  # every rule at least once
        data = random_input(r)
        b(data, r)
        cases.append({"kind": "simulate", "input": data})
    for _ in range(n_compare):
        cases.append({"kind": "compare", "inputs": [random_input(r) for _ in range(r.randint(2, 5))]})
    for _ in range(n_ladder):
        data = random_input(r)
        amounts = sorted(_amount(r, 0, data["list_price"] * 0.3) for _ in range(r.randint(1, 6)))
        cases.append({"kind": "cash_ladder", "input": data, "amounts": amounts})
    return cases


def build() -> list[dict]:
    recorded_path = RESULTS / "behave_calls.json"
    if not recorded_path.is_file():
        raise SystemExit(f"{recorded_path} is missing: run `python harness/run_features.py --engine cpython "
                         f"--record results/behave_calls.json` first")
    recorded = [{**c, "source": "behave"} for c in json.loads(recorded_path.read_text())]
    return (recorded + [{**c, "source": "reference"} for c in reference_cases()]
            + [{**c, "source": "random"} for c in random_cases()])


def request_of(case: dict) -> dict:
    return {k: v for k, v in case.items() if k not in ("kind", "source")}


def expected(case: dict) -> dict:
    """What CPython answers: the reply of the same bridge the in-browser Python runtimes use."""
    return json.loads(bridge.call(case["kind"], json.dumps(request_of(case))))


if __name__ == "__main__":
    cases = build()
    by = {}
    for c in cases:
        reply = expected(c)
        key = (c["source"], c["kind"], "ok" if reply["ok"] else reply["kind"])
        by[key] = by.get(key, 0) + 1
    for k, v in sorted(by.items()):
        print(*k, v)
    print("total", len(cases))
