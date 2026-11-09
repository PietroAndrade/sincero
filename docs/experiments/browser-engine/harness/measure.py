"""
What each engine costs a user, measured in headless Chromium against harness/serve.py (gzip on,
10-minute cache, like a static host):

  download     bytes on the wire for the first visit (CDP `encodedDataLength`), and the size of
               each runtime file raw / gzipped
  first result time from navigation to the first result on screen (engine loaded + RA simulated
               + cash ladder + rendered): first visit (empty cache) and repeat visit (HTTP cache)
  per update   warm time of what the UI runs on every keystroke: simulate RA + a 4-rung cash
               ladder, call + JSON parse (`window.sincero.bench`)

Two profiles: `desktop` (no throttling) and `phone`, Lighthouse's mobile throttling (150 ms RTT,
1.6 Mbit/s down, 750 kbit/s up, CPU slowed 4x) — a harsh, standard reference, not a typical phone.
Medians of --runs runs.

    python harness/measure.py [--runs 3] [--engine ts pyodide brython]   -> results/measure.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from browser import ENGINES, RESULTS, browser
from serve import DIST, _gzipped

PROFILES = {
    "desktop": None,
    "phone": {"latency": 150, "downloadThroughput": 1638.4 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8, "cpu": 4},
}
RA = {"name": "RA", "list_price": 440000, "months_remaining": 19, "fgts_upfront": 13000}


def runtime_files(engine: str) -> list[Path]:
    common = [DIST / "index.html", DIST / "style.css", DIST / "app.js"]
    extra = {
        "ts": [],
        "pyodide": sorted((DIST / "pyodide").iterdir()) + [DIST / "py" / "engine.json"],
        "brython": sorted((DIST / "brython").iterdir()) + sorted((DIST / "py").rglob("*.py")),
    }[engine]
    return common + extra


def file_sizes(engine: str) -> dict:
    files = runtime_files(engine)
    raw = sum(f.stat().st_size for f in files)
    gz = sum(len(_gzipped(f, f.stat().st_mtime)) for f in files)
    return {"files": len(files), "raw_bytes": raw, "gzip_bytes": gz}


def visit(b, url: str, engine: str, profile: str) -> dict:
    """One first visit and one repeat visit (reload, HTTP cache warm) in a fresh context."""
    context = b.new_context()
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    conditions = PROFILES[profile]
    if conditions:
        cdp.send("Network.emulateNetworkConditions", {"offline": False, **{k: v for k, v in conditions.items() if k != "cpu"}})
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": conditions["cpu"]})
    wire = {"bytes": 0}
    cdp.on("Network.loadingFinished", lambda e: wire.__setitem__("bytes", wire["bytes"] + e["encodedDataLength"]))

    out = {}
    # wait_until="commit": the engine-ready check below is the real wait (Brython's injected scripts
    # hold back the `load` event for longer than Playwright's 30 s default on the phone profile)
    for label, go in (("first", lambda: page.goto(f"{url}?engine={engine}", wait_until="commit", timeout=600_000)),
                      ("repeat", lambda: page.reload(wait_until="commit", timeout=600_000))):
        wire["bytes"] = 0
        go()
        page.wait_for_function("window.sincero && window.sincero.state !== 'loading'", timeout=600_000)
        t = page.evaluate("window.sincero.timings")
        out[label] = {"wire_bytes": wire["bytes"], "ready_ms": t["ready"], "first_result_ms": t["firstResult"]}
    # warm: what one keystroke costs (simulate + cash ladder), after the visits above
    n = 40 if engine != "brython" else 8
    sim = json.dumps({"input": RA})
    ladder = json.dumps({"input": RA, "amounts": [0, 30000, 75000, 100000]})
    page.evaluate("([s, l]) => { window.sincero.bench('simulate', s, 3); window.sincero.bench('cash_ladder', l, 3); }", [sim, ladder])
    out["simulate_ms"] = page.evaluate("([s, n]) => window.sincero.bench('simulate', s, n)", [sim, n])
    out["cash_ladder_ms"] = page.evaluate("([l, n]) => window.sincero.bench('cash_ladder', l, n)", [ladder, n])
    context.close()
    return out


def median_of(runs: list[dict], *path: str) -> float:
    values = []
    for r in runs:
        for p in path:
            r = r[p]
        values.append(r)
    return statistics.median(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--engine", nargs="*", choices=ENGINES, default=list(ENGINES))
    args = parser.parse_args()

    report: dict = {"profiles": {k: v for k, v in PROFILES.items()}, "engines": {}}
    with browser() as (b, url):
        report["browser"] = f"{b.browser_type.name} {b.version}"
        for engine in args.engine:
            entry = {"sizes": file_sizes(engine)}
            for profile in PROFILES:
                runs = [visit(b, url, engine, profile) for _ in range(args.runs)]
                entry[profile] = {
                    "runs": runs,
                    "first_visit_wire_bytes": median_of(runs, "first", "wire_bytes"),
                    "first_visit_first_result_ms": median_of(runs, "first", "first_result_ms"),
                    "repeat_visit_wire_bytes": median_of(runs, "repeat", "wire_bytes"),
                    "repeat_visit_first_result_ms": median_of(runs, "repeat", "first_result_ms"),
                    "update_ms": median_of(runs, "simulate_ms") + median_of(runs, "cash_ladder_ms"),
                    "simulate_ms": median_of(runs, "simulate_ms"),
                    "cash_ladder_ms": median_of(runs, "cash_ladder_ms"),
                }
                e = entry[profile]
                print(f"{engine:8} {profile:8} first visit: {e['first_visit_wire_bytes'] / 1e6:6.2f} MB, "
                      f"first result {e['first_visit_first_result_ms'] / 1000:5.1f} s | repeat visit: "
                      f"{e['repeat_visit_wire_bytes'] / 1e6:5.2f} MB, {e['repeat_visit_first_result_ms'] / 1000:5.1f} s | "
                      f"per update {e['update_ms']:7.1f} ms (simulate {e['simulate_ms']:.1f} + ladder {e['cash_ladder_ms']:.1f})",
                      flush=True)
            s = entry["sizes"]
            print(f"{engine:8} files: {s['files']}, {s['raw_bytes'] / 1e6:.2f} MB raw, {s['gzip_bytes'] / 1e6:.2f} MB gzip", flush=True)
            report["engines"][engine] = entry
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "measure.json"
    previous = json.loads(out.read_text()) if out.is_file() else {"engines": {}}
    report["engines"] = {**previous.get("engines", {}), **report["engines"]}   # --engine X updates X only
    out.write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
