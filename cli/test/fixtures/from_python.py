"""
Record what the retired Python CLI (`python cli.py …`) prints, so the Node CLI can be held to it
(plan item P3.1: "the README's CLI examples print the same figures"). Run once, from the
repository root, with CPython >= 3.12:

    python3 cli/test/fixtures/from_python.py [--backend legacy/backend]

Writes cli/test/fixtures/python-cli.json: for each argument list, the exit code and either the exact
stdout (the text report, the tables, the error lines) or, for --json, the golden master's digest of
the parsed payload (Python prints 440000.0 where JavaScript prints 440000: the same number).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("python-cli.json")

# The README's examples first, then what they do not reach.
CASES: list[tuple[str, list[str]]] = [
    ("README: the five reference properties", []),
    ("README: one property with a developer plan",
     ["--name", "RA", "--price", "440000", "--months", "19", "--fgts", "13000",
      "--installment", "2500", "--balloon-month", "6", "--balloon-month", "12"]),
    ("README: the cash ladder", ["--price", "440000", "--months", "19", "--fgts", "13000", "--cash-ladder", "0,30000,75000,100000"]),
    ("README: closing costs, income ceiling, pro-soluto",
     ["--price", "440000", "--months", "19", "--itbi", "3", "--registry", "1", "--income-ratio", "0.35", "--pro-soluto-months", "24"]),
    ("README: the JSON payload", ["--price", "440000", "--months", "19", "--json"]),
    ("the cash ladder as JSON", ["--price", "440000", "--months", "19", "--fgts", "13000", "--cash-ladder", "0,30000", "--json"]),
    ("every other flag",
     ["--name", "Apto 12", "--price", "512345.67", "--months", "36", "--down-payment-pct", "25.5", "--cash", "15000.25",
      "--incc", "6.1", "--bank-rate", "11.49", "--term", "420", "--pre-approved", "350000"]),
    ("--flag=value", ["--price=440000", "--months=19", "--fgts=13000"]),
    ("a negative rate as a value", ["--price", "440000", "--months", "19", "--incc", "-2"]),
    ("half-cent ties in the report", ["--price", "300000.125", "--months", "4", "--fgts", "0.375"]),
    ("a cash purchase", ["--price", "440000", "--months", "19", "--cash", "440000"]),
    ("a pre-approval above the need: no gap", ["--price", "440000", "--months", "19", "--pre-approved", "500000"]),
    ("--json ignored without --price: the reference run", ["--json"]),
    ("error: months", ["--price", "440000", "--months", "0"]),
    ("error: upfront above the list price", ["--price", "440000", "--months", "19", "--cash", "500000"]),
    ("error: installments leave a balance", ["--price", "440000", "--months", "19", "--fgts", "13000", "--installment", "2500"]),
    ("error: in the ladder, a rung's own rule", ["--price", "440000", "--months", "19", "--fgts", "13000", "--cash-ladder", "0,430000"]),
]


def digest_of(payload) -> str:
    spec = importlib.util.spec_from_file_location("golden", ROOT / "engine" / "golden" / "tools" / "from_python.py")
    golden = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(golden)
    return golden.digest(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", type=Path, default=ROOT / "legacy" / "backend")
    backend = parser.parse_args().backend.resolve()
    if not (backend / "cli.py").is_file():
        raise SystemExit(f"{backend} has no cli.py: point --backend at the retired backend/")
    cases = []
    for note, argv in CASES:
        run = subprocess.run([sys.executable, "cli.py", *argv], cwd=backend, capture_output=True, text=True)
        if run.stderr:
            raise SystemExit(f"{note}: the Python CLI wrote to stderr:\n{run.stderr}")
        case = {"note": note, "argv": argv, "exit": run.returncode}
        if "--json" in argv and "--price" in " ".join(argv) and run.returncode == 0:
            case["json_digest"] = digest_of(json.loads(run.stdout))
        else:
            case["stdout"] = run.stdout
        cases.append(case)
        print(f"{run.returncode}  {note}")
    OUT.write_text(json.dumps({"about": "What the retired Python CLI printed: see from_python.py.",
                               "python": sys.version.split()[0], "cases": cases}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(cases)} cases -> {OUT} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
