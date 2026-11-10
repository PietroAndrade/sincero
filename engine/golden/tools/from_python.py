"""
Freeze the retired Python engine's answers as the engine package's golden master (plan item P1.3).

Run once, from the repository root, with CPython >= 3.12 and behave (behave only records the
scenarios' inputs; the engine itself is standard library only):

    python3 -m venv /tmp/oracle && /tmp/oracle/bin/pip install behave
    /tmp/oracle/bin/python engine/golden/tools/from_python.py [--backend legacy/backend]

`--backend` is the retired backend/ directory: `legacy/backend`, or a worktree of the tag
`python-engine-final` (`git worktree add /tmp/py python-engine-final`, then `--backend /tmp/py/backend`).
It writes two files, one case per line so that a change reads as a diff:

    engine/golden/corpus.json    the inputs (what to ask the engine)
    engine/golden/expected.json  the Python engine's answers (one SHA-256 per case over the exact bits
                                 of the reply, the message of each rejection) and the `**` probes

The corpus (docs/experiments/browser-engine/harness/corpus.py, same seed, so the first 429 cases are
the experiment's):

    behave     every simulate/compare call the 54 scenarios make, recorded while behave runs the
               retired engine (the suite must pass, or nothing is written)
    reference  the five reference properties of the CLI, each simulated and cash-laddered, compared
    random     seeded inputs over the whole input space, one broken rule in ~1 case in 8, every rule
    targeted   edges the random cases miss: repeated or colliding cash-ladder amounts, what-ifs,
               half-cent ties in the messages at every magnitude

After this runs once, the figures change only on purpose: see engine/golden/README.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GOLDEN = ROOT / "engine" / "golden"


# ----- the digest (engine/test/digest.ts computes the same one in TypeScript) ---------------------
def feed(h, x) -> None:
    if x is None:
        h.update(b"N")
    elif isinstance(x, bool):
        h.update(b"T" if x else b"F")
    elif isinstance(x, (int, float)):
        x = float(x)
        x = 0.0 if x == 0 else x  # canonical: -0.0 -> 0.0
        h.update(b"D" + struct.pack(">d", x))
    elif isinstance(x, str):
        b = x.encode()
        h.update(b"S" + struct.pack(">I", len(b)) + b)
    elif isinstance(x, list):
        h.update(b"L" + struct.pack(">I", len(x)))
        for v in x:
            feed(h, v)
    elif isinstance(x, dict):
        h.update(b"M" + struct.pack(">I", len(x)))
        for k in sorted(x):
            feed(h, k)
            feed(h, x[k])
    else:
        raise TypeError(type(x))


def digest(reply: dict) -> str:
    h = hashlib.sha256()
    feed(h, reply)
    return h.hexdigest()


# ----- the corpus (from the experiment's harness/corpus.py, unchanged apart from layout) ----------
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


def targeted_cases() -> list[dict]:
    """Edges the random cases do not reach, each named by `note`."""
    ra = {"name": "RA", "list_price": 440_000, "months_remaining": 19, "fgts_upfront": 13_000}
    ra_plan = {**ra, "developer_installment": 2_500, "balloon_months": [6, 12]}
    tie = 2**49 + 0.125  # the smallest magnitude where a half-cent tie is not exact in doubles × 100
    ladder = lambda note, amounts, base=ra: {"kind": "cash_ladder", "note": note, "input": base, "amounts": amounts}  # noqa: E731
    what_if = lambda note, variations, base=ra: {"kind": "what_if", "note": note, "input": base, "variations": variations}  # noqa: E731
    simulate = lambda note, data: {"kind": "simulate", "note": note, "input": data}  # noqa: E731
    return [
        ladder("repeated amounts are one variation (a dict's keys)", [0, 30_000, 30_000, 75_000]),
        ladder("amounts equal to the cent share a label: first position, last amount", [30_000.001, 0, 30_000.004]),
        ladder("unsorted amounts are accepted today (P1.6 will refuse them)", [100_000, 0, 30_000]),
        ladder("a negative amount is a rejected input", [0, -1_000]),
        ladder("an amount above the list price is a rejected input", [0, 500_000]),
        ladder("an empty ladder is the base alone", []),
        ladder("the ladder over a plan with balloons", [0, 10_000, 20_000], ra_plan),
        ladder("cash that makes the installments exceed the balance rejects the ladder", [0, 50_000], ra_plan),
        ladder("-0.0 is not negative, and its label is `cash -0.00`; ties in labels", [-0.0, 30_000.125, 30_000.375]),
        what_if("one variation per input group", [
            ["low INCC", {"incc_rate_pa": 4.0}], ["more cash", {"cash_upfront": 30_000}],
            ["cheaper bank", {"bank_rate_pa": 8.5}], ["longer term", {"term_months": 420}],
            ["credit", {"pre_approved_credit": 300_000, "pro_soluto_months": 24}],
        ]),
        what_if("a repeated label keeps its first position and its last overrides",
                [["x", {"incc_rate_pa": 4.0}], ["y", {"bank_rate_pa": 8.0}], ["x", {"incc_rate_pa": 9.0}]]),
        what_if("overrides that change the developer plan", [
            ["no plan", {"developer_installment": None, "balloon_months": []}],
            ["other balloons", {"balloon_months": [3, 9, 18]}],
        ], ra_plan),
        what_if("a variation breaking a rule rejects the whole what-if", [["ok", {}], ["broken", {"term_months": 0}]]),
        what_if("an unknown override is a shape error", [["typo", {"incc": 4.0}]]),
        what_if("no variations", []),
        simulate("half-cent tie at 2^49 in the message", {**ra, "list_price": tie, "fgts_upfront": tie, "cash_upfront": 1.0}),
        simulate("half-cent tie at 2^50 - 1/8 in the message",
                 {**ra, "list_price": 2**50 - 0.125, "fgts_upfront": 2**50 - 0.125, "cash_upfront": 0.125}),
        simulate("amounts from 1e21 up in the message", {**ra, "list_price": 1e21, "fgts_upfront": 3e21}),
        simulate("a cash purchase", {**ra, "fgts_upfront": 0, "cash_upfront": 440_000}),
        simulate("every field set", {
            "name": "all", "list_price": 512_345.67, "months_remaining": 36, "down_payment_pct": 25.5,
            "fgts_upfront": 20_000.5, "cash_upfront": 15_000.25, "developer_installment": 1_000,
            "balloon_months": [12, 24, 36], "incc_rate_pa": 6.1, "bank_rate_pa": 11.49, "term_months": 420,
            "itbi_pct": 3.0, "registry_pct": 1.0, "income_commitment_ratio": 0.35,
            "pre_approved_credit": 350_000, "pro_soluto_months": 30}),
        simulate("one month to delivery, one month of financing",
                 {**ra, "months_remaining": 1, "term_months": 1}),
    ]


# ----- asking the retired engine ---------------------------------------------------------------
def record_behave_calls(backend: Path) -> list[dict]:
    """Run the 54 scenarios against the retired engine and keep every call they make."""
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    import support.gateway as gateway
    from behave.__main__ import main as behave_main

    calls: list[dict] = []

    class RecordingGateway(gateway.EngineGateway):
        def simulate(self, data):
            calls.append({"kind": "simulate", "input": dict(data)})
            return super().simulate(data)

        def compare(self, rows):
            calls.append({"kind": "compare", "inputs": [dict(r) for r in rows]})
            return super().compare(rows)

    gateway.EngineGateway = RecordingGateway
    status = behave_main(["features", "--format", "progress", "--no-capture"])
    if status != 0:
        raise SystemExit(f"behave failed on the retired engine (exit {status}): nothing written")
    return json.loads(json.dumps(calls, default=list))  # tuples -> lists, as JSON will hold them


def python_engine(backend: Path):
    """The replies of the retired engine, in the shape of the experiment's sincero_bridge.py."""
    sys.path.insert(0, str(backend))
    from app.models import SimulationError, cash_ladder, compare, simulate, what_if
    from app.views import comparison_to_dict, input_from_dict, simulation_to_dict, what_if_to_dict

    def answer(case: dict) -> dict:
        try:
            kind = case["kind"]
            if kind == "simulate":
                value = simulation_to_dict(simulate(input_from_dict(case["input"])))
            elif kind == "compare":
                value = comparison_to_dict(compare([input_from_dict(r) for r in case["inputs"]]))
            elif kind == "cash_ladder":
                value = what_if_to_dict(cash_ladder(input_from_dict(case["input"]), case["amounts"]))
            elif kind == "what_if":
                value = what_if_to_dict(what_if(input_from_dict(case["input"]), dict(case["variations"])))
            else:
                raise ValueError(f"unknown kind {kind}")
        except SimulationError as exc:
            return {"ok": False, "kind": "rejected", "error": str(exc)}
        except TypeError:
            # an unknown or missing field: the text is CPython's own, so only the outcome is kept
            return {"ok": False, "kind": "invalid_shape"}
        # through JSON, as the answer of a JSON API would be: tuples -> lists, ints stay ints
        return {"ok": True, "value": json.loads(json.dumps(value))}

    return answer


def pow_probes(n: int = 400) -> list[list]:
    """CPython's `**` on the engine's two shapes of power (harness probes/pow_cases.py, smaller)."""
    r = random.Random(1)
    probes = []
    for _ in range(n):
        rate = r.uniform(-20, 30)
        monthly = (1 + rate / 100) ** (1 / 12) - 1
        k = r.randint(1, 420)
        probes.append([rate, k, monthly, (1 + monthly) ** k])
    return probes


# ----- writing ---------------------------------------------------------------------------------
def dump_lines(path: Path, head: dict, lists: dict[str, list]) -> None:
    """JSON with `head` indented and one item per line in each of `lists`: a changed case is a one-line diff."""
    parts = [f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in head.items()]
    for key, items in lists.items():
        lines = ",\n    ".join(json.dumps(i, ensure_ascii=False, separators=(",", ":")) for i in items)
        parts.append(f"  {json.dumps(key)}: [\n    {lines}\n  ]")
    text = "{\n" + ",\n".join(parts) + "\n}\n"
    json.loads(text)  # well-formed, or fail here rather than in the test
    path.write_text(text, encoding="utf-8")


def git_describe(backend: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(backend), "log", "-1", "--format=%h %cs", "--", "."],
                             capture_output=True, text=True, check=True).stdout.strip()
        return out or "uncommitted"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", type=Path, default=ROOT / "legacy" / "backend",
                        help="the retired backend/ directory (default: legacy/backend)")
    args = parser.parse_args()
    backend = args.backend.resolve()
    if sys.version_info < (3, 12):
        raise SystemExit("CPython >= 3.12 is the oracle: sum() of floats is compensated from 3.12 on")
    if not (backend / "app" / "models").is_dir():
        raise SystemExit(f"{backend} has no app/models: point --backend at the retired backend/")

    recorded = record_behave_calls(backend)
    cases = ([{**c, "source": "behave"} for c in recorded]
             + [{**c, "source": "reference"} for c in reference_cases()]
             + [{**c, "source": "random"} for c in random_cases()]
             + [{**c, "source": "targeted"} for c in targeted_cases()])
    # The engine answers the corpus as read back from JSON: exactly what the TypeScript test will read.
    corpus = json.loads(json.dumps([{"id": i, **c} for i, c in enumerate(cases)]))

    answer = python_engine(backend)
    expected = []
    for case in corpus:
        reply = answer(case)
        entry: dict = {"id": case["id"], "outcome": "ok" if reply["ok"] else reply["kind"]}
        if reply.get("kind") == "rejected":
            entry["error"] = reply["error"]
        if reply.get("kind") != "invalid_shape":
            entry["digest"] = digest(reply)
        expected.append(entry)

    GOLDEN.mkdir(parents=True, exist_ok=True)
    dump_lines(GOLDEN / "corpus.json", {
        "about": "The inputs of the golden master: see engine/golden/README.md. Written by "
                 "engine/golden/tools/from_python.py; `id` is the index.",
    }, {"cases": corpus})
    dump_lines(GOLDEN / "expected.json", {
        "about": "The retired Python engine's answers to corpus.json, by id: see engine/golden/README.md.",
        "oracle": {
            "engine": f"backend/ at {git_describe(backend)} (tag python-engine-final)",
            "python": f"{platform.python_implementation()} {platform.python_version()}",
        },
        "digest": "SHA-256 over the reply {ok, value} or {ok, kind, error}: engine/test/digest.ts",
    }, {"pow_probes": pow_probes(), "cases": expected})
    by: dict = {}
    for c, e in zip(corpus, expected):
        by[(c["source"], e["outcome"])] = by.get((c["source"], e["outcome"]), 0) + 1
    print(f"\n{len(corpus)} cases:", ", ".join(f"{s}/{o} {n}" for (s, o), n in sorted(by.items())))
    for name in ("corpus.json", "expected.json"):
        print(f"  {GOLDEN / name}: {(GOLDEN / name).stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
