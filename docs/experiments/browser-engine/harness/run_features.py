"""
Run the backend's behave suite (backend/features/, the 54 business scenarios) through an engine
running INSIDE the browser page — the same page a buyer opens — instead of the Python engine
in this process. Nothing in backend/ changes: the suite talks to the application through one
class, `support.gateway.EngineGateway`, and this script swaps it before behave loads the hooks.

    python harness/run_features.py --engine ts          # the TypeScript port, in Chromium
    python harness/run_features.py --engine pyodide     # the unchanged Python engine, in Chromium
    python harness/run_features.py --engine brython
    python harness/run_features.py --engine cpython --record results/behave_calls.json
                                                        # the normal run; records every call for the corpus
Exit code: behave's.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from browser import BACKEND, ENGINES, EngineRejected, browser, call, open_engine


class BrowserGateway:
    """`EngineGateway`'s interface (simulate, compare, error_type), answered by the page."""

    error_type = EngineRejected

    def __init__(self, page):
        self.page = page

    def simulate(self, data: dict) -> dict:
        return call(self.page, "simulate", {"input": data})

    def compare(self, rows: list[dict]) -> list[dict]:
        return call(self.page, "compare", {"inputs": rows})


def run_behave(extra: list[str]) -> int:
    from behave.__main__ import main as behave_main
    return behave_main(["features", "--format", "progress", "--no-capture", *extra])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=("cpython", *ENGINES), required=True)
    parser.add_argument("--record", type=Path, help="cpython only: write every simulate/compare input to this file")
    parser.add_argument("behave_args", nargs="*", help="passed to behave (after --), e.g. -- --tags=@more-cash")
    args = parser.parse_args()
    record_to = args.record.resolve() if args.record else None

    os.chdir(BACKEND)
    import support.gateway as gateway  # noqa: E402  (after chdir/sys.path: backend/ is importable)

    if args.engine == "cpython":
        calls: list[dict] = []

        class RecordingGateway(gateway.EngineGateway):
            def simulate(self, data):
                calls.append({"kind": "simulate", "input": dict(data)})
                return super().simulate(data)

            def compare(self, rows):
                calls.append({"kind": "compare", "inputs": [dict(r) for r in rows]})
                return super().compare(rows)

        gateway.EngineGateway = RecordingGateway
        status = run_behave(args.behave_args)
        if record_to:
            record_to.parent.mkdir(parents=True, exist_ok=True)
            record_to.write_text(json.dumps(calls, default=list))
            print(f"recorded {len(calls)} calls -> {record_to}")
        return status

    with browser() as (b, url):
        page = open_engine(b, url, args.engine)
        gateway.EngineGateway = lambda: BrowserGateway(page)   # features/environment.py: `_engine = EngineGateway()`
        print(f"engine: {args.engine} in {b.browser_type.name} {b.version}")
        return run_behave(args.behave_args)


if __name__ == "__main__":
    sys.exit(main())
