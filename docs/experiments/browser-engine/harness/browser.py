"""
Drive the built page (dist/) in headless Chromium: one page per engine, and a `call` that goes
through `window.sincero.callJson`, exactly the path the UI uses.

Chromium: Playwright's own (`python -m playwright install chromium`), or the executable named by
`CHROME_PATH` (the sandbox this was written in had a pre-installed build under /opt/pw-browsers).
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from playwright.sync_api import Browser, Page, sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                    # docs/experiments/browser-engine
BACKEND = ROOT.parents[2] / "backend"                 # the repository's backend/
RESULTS = ROOT / "results"
ENGINES = ("ts", "pyodide", "brython")

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BACKEND))
from serve import start  # noqa: E402


@contextmanager
def browser() -> Iterator[tuple[Browser, str]]:
    """A headless Chromium and the base URL of a fresh static server for dist/."""
    server, url = start()
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROME_PATH")
            b = p.chromium.launch(**({"executable_path": exe} if exe else {}))
            try:
                yield b, url
            finally:
                b.close()
    finally:
        server.shutdown()


def open_engine(b: Browser, url: str, engine: str, timeout_ms: int = 180_000, **context: Any) -> Page:
    """A new page on `?engine=…`, once the engine has loaded and the first result is on screen."""
    page = b.new_context(**context).new_page()
    page.goto(f"{url}?engine={engine}")
    page.wait_for_function("window.sincero && window.sincero.state !== 'loading'", timeout=timeout_ms)
    if page.evaluate("window.sincero.state") != "ready":
        raise RuntimeError(f"{engine}: {page.evaluate('window.sincero.error')}")
    return page


class EngineRejected(Exception):
    """The engine refused the input (a `SimulationError`); the message is the model's, verbatim."""


class InvalidShape(Exception):
    """Unknown or missing field (`TypeError` in Python)."""


def call(page: Page, kind: str, request: dict) -> Any:
    reply = json.loads(page.evaluate("([k, r]) => window.sincero.callJson(k, r)", [kind, json.dumps(request)]))
    if reply["ok"]:
        return reply["value"]
    raise (EngineRejected if reply["kind"] == "rejected" else InvalidShape)(reply["error"])
