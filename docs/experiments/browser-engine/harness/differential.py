"""
Differential test: every case of the corpus (harness/corpus.py) through each engine in the browser
page, against CPython running the same bridge in this process. Stricter than behave, which
reads ~400 figures with a half-cent tolerance: here EVERY number of every payload (the three
schedules included, ~20,000 numbers per simulation) is compared, and counted as bit-identical or
not; every rejection must carry the same message, verbatim.

    python harness/differential.py [--engine ts pyodide brython]     -> results/differential.json
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
from dataclasses import asdict, dataclass, field

from browser import ENGINES, RESULTS, browser, open_engine
import corpus

HALF_CENT = 0.005


def ulps(a: float, b: float) -> int:
    """Distance between two doubles in units in the last place (0: the same double)."""
    def ordered(x: float) -> int:
        i = struct.unpack("<q", struct.pack("<d", x))[0]
        return i if i >= 0 else -(i & 0x7FFF_FFFF_FFFF_FFFF)
    return abs(ordered(a) - ordered(b))


@dataclass
class Stats:
    cases: int = 0
    outcome_mismatches: list = field(default_factory=list)   # ok vs rejected vs invalid_shape
    message_mismatches: list = field(default_factory=list)   # same outcome, different text
    structure_mismatches: list = field(default_factory=list)  # keys, lengths, types
    numbers: int = 0
    identical: int = 0
    max_ulps: int = 0                                         # between same-sign doubles with |x| >= 1e-6
    near_zero: int = 0                                        # cancellation residuals (|x| < 1e-6, sign flips): ulps mean nothing
    max_abs: float = 0.0
    max_abs_path: str = ""
    max_rel: float = 0.0
    max_rel_path: str = ""
    over_half_cent: int = 0
    seconds: float = 0.0

    def compare(self, exp, got, path: str, case_no: int) -> None:
        if isinstance(exp, bool) or isinstance(got, bool):
            if exp is not got:
                self.structure_mismatches.append((case_no, path, repr(exp), repr(got)))
        elif isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            self.numbers += 1
            a, b = float(exp), float(got)
            if a == b:
                self.identical += 1
                return
            d = abs(a - b)
            rel = d / max(abs(a), abs(b))
            if (a < 0) != (b < 0) or min(abs(a), abs(b)) < 1e-6:
                self.near_zero += 1
            else:
                self.max_ulps = max(self.max_ulps, ulps(a, b))
            if d > self.max_abs:
                self.max_abs, self.max_abs_path = d, f"case {case_no}: {path} ({a!r} vs {b!r})"
            if rel > self.max_rel:
                self.max_rel, self.max_rel_path = rel, f"case {case_no}: {path} ({a!r} vs {b!r})"
            if d > HALF_CENT:
                self.over_half_cent += 1
        elif isinstance(exp, dict) and isinstance(got, dict):
            if set(exp) != set(got):
                self.structure_mismatches.append((case_no, path, sorted(set(exp) ^ set(got)), ""))
            for k in exp.keys() & got.keys():
                self.compare(exp[k], got[k], f"{path}.{k}" if path else k, case_no)
        elif isinstance(exp, list) and isinstance(got, list):
            if len(exp) != len(got):
                self.structure_mismatches.append((case_no, path, f"len {len(exp)}", f"len {len(got)}"))
            for i, (e, g) in enumerate(zip(exp, got)):
                self.compare(e, g, f"{path}[{i}]", case_no)
        elif exp != got:
            self.structure_mismatches.append((case_no, path, repr(exp), repr(got)))


def outcome(reply: dict) -> str:
    return "ok" if reply["ok"] else reply["kind"]


def run_engine(b, url, engine: str, cases: list[dict], expected: list[dict]) -> Stats:
    page = open_engine(b, url, engine)
    stats = Stats()
    t0 = time.perf_counter()
    for i, (case, exp) in enumerate(zip(cases, expected)):
        got = json.loads(page.evaluate("([k, r]) => window.sincero.callJson(k, r)",
                                       [case["kind"], json.dumps(corpus.request_of(case))]))
        stats.cases += 1
        if outcome(exp) != outcome(got):
            stats.outcome_mismatches.append((i, outcome(exp), outcome(got), got.get("error", "")))
        elif not exp["ok"]:
            # a TypeError's text is CPython's own ("ContractData.__init__() missing…"); only the kind must agree
            if exp["kind"] == "rejected" and exp["error"] != got["error"]:
                stats.message_mismatches.append((i, exp["error"], got["error"]))
        else:
            stats.compare(exp["value"], got["value"], "", i)
    stats.seconds = time.perf_counter() - t0
    page.context.close()
    return stats


def check_fields(b, url) -> list[str]:
    """The TypeScript port's field table against the Python DTOs (generated from the .proto)."""
    import dataclasses
    from app.models.input_dto import INPUT_GROUPS
    group = dict(zip(INPUT_GROUPS, ("contract", "market", "bank_credit")))
    python = []
    for dto in INPUT_GROUPS:
        for f in dataclasses.fields(dto):
            if f.default is not dataclasses.MISSING:
                default = f.default
            elif f.default_factory is not dataclasses.MISSING:
                default = list(f.default_factory())
            else:
                default = "<required>"
            python.append({"name": f.name, "group": group[dto], "default": default})
    page = open_engine(b, url, "ts")
    ts = [{"name": f["name"], "group": f["group"], "default": f.get("default", "<required>")}
          for f in page.evaluate("window.sincero.fields")]
    page.context.close()
    return [f"TypeScript {t} != Python {p}" for t, p in zip(ts, python) if t != p] + \
        ([f"{len(ts)} fields in TypeScript, {len(python)} in Python"] if len(ts) != len(python) else [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", nargs="*", choices=ENGINES, default=list(ENGINES))
    args = parser.parse_args()

    cases = corpus.build()
    expected = [corpus.expected(c) for c in cases]
    report: dict = {"cases": len(cases), "engines": {}}
    failed = False
    with browser() as (b, url):
        report["browser"] = f"{b.browser_type.name} {b.version}"
        report["ts_field_table_drift"] = check_fields(b, url)
        failed |= bool(report["ts_field_table_drift"])
        for engine in args.engine:
            s = run_engine(b, url, engine, cases, expected)
            report["engines"][engine] = asdict(s)
            bad = s.outcome_mismatches or s.message_mismatches or s.structure_mismatches or s.over_half_cent
            failed |= bool(bad)
            print(f"\n== {engine}: {s.cases} cases in {s.seconds:.1f} s")
            print(f"   outcomes that differ (ok / rejected / invalid shape): {len(s.outcome_mismatches)}")
            print(f"   rejection messages that differ:                      {len(s.message_mismatches)}")
            print(f"   payload structure that differs:                      {len(s.structure_mismatches)}")
            pct = 100 * s.identical / s.numbers if s.numbers else math.nan
            print(f"   numbers compared: {s.numbers:,}; bit-identical: {s.identical:,} ({pct:.4f}%)")
            print(f"   largest difference: {s.max_ulps} ulp (|x| >= 1e-6; near-zero residuals: {s.near_zero}); abs {s.max_abs:.3g} [{s.max_abs_path}]")
            print(f"                       rel {s.max_rel:.3g} [{s.max_rel_path}]")
            print(f"   figures off by more than half a cent: {s.over_half_cent}")
            for m in (s.outcome_mismatches + s.message_mismatches + s.structure_mismatches)[:5]:
                print("   !", m)
    print(f"\nTypeScript field table vs Python DTOs: {report['ts_field_table_drift'] or 'identical'}")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "differential.json").write_text(json.dumps(report, indent=2, default=str))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
