# Decision: the engine runs in the browser, in TypeScript; the Python engine and the protobuf contract are retired

*Status: accepted, 2026-11-09. Evidence:
[`../experiments/browser-engine/`](../experiments/browser-engine/README.md) (a TypeScript port,
bit-identical to the Python engine on 1,791,838 figures, 0.7–1.0 s to the first result on a throttled
phone against 47–53 s for Python in the browser). The plan that carries it out is
[`../plan/typescript-port.md`](../plan/typescript-port.md). Supersedes
[api-protocol-and-language](api-protocol-and-language.md) for the web path: the buyer's page has no
server and no API. The business rules, the 54 scenarios (their text), the figures and the JSON
payload of a simulation are untouched.*

## Context

SINCERO should work for people who cannot run Python, on a phone, without installing anything. A
static page is the shortest path, and the engine is pure computation with no I/O, so it can run in
the browser. The experiment compared the unchanged Python engine in the browser (Pyodide, Brython)
with a TypeScript port. Only the port is fast enough for a buyer on a phone, and the differential
harness shows it gives Python's figures to the bit.

With the engine in the page there is no server to put an API on. The Connect service (milestone 5,
tasks 5.5–5.14), Docker (milestone 7) and the server-side concerns (CORS, abuse protection, hosting a
process) have nothing to protect or run.

## Decisions

The letters are those of the plan's table.

| # | Decision | Answer |
|---|---|---|
| A | Python's end | **Retired now, not after gate G2.** The branch [`legacy/python-engine`](https://github.com/PietroAndrade/sincero/tree/legacy/python-engine) and the annotated tag `python-engine-final` hold the last commit with `backend/` (`6b14ecb`); `backend/` was then removed from `develop`. See [what the early retirement changes](#what-the-early-retirement-changes) |
| B | Protobuf | **Retired with Python.** The `.proto` files and the generated code are on the branch and the tag; the field table (names, groups, defaults, units, labels) becomes TypeScript. [A public API later](../plan/typescript-port.md#a-public-api-later) says how to bring them back |
| C | CLI | **Port to Node** (phase 3), same flags as `cli.py` |
| D | UI stack | **Vite + React**; charts with uPlot, Chart.js or SVG, **not Plotly** (386 KB gzipped against a 12.9 KB engine) |
| E | Tests | **vitest** (unit, golden master), **cucumber-js** (the `.feature` files), **@playwright/test** (end to end) |
| F | Layout | **npm workspaces**: `engine/`, `features/`, `web/`, `cli/`, `e2e/`; Node ≥ 24 pinned |

Python is **frozen** by being gone from `develop`: no behaviour is added to it. If a bug in the
retired engine matters (it is the oracle of the golden master), the fix is made on
`legacy/python-engine` and the golden master regenerated from there.

## What the early retirement changes

The plan retired Python after the TypeScript engine passed the specification (G2), so that two engines
ran side by side for a while. They did not: Python left first. What that changes in the plan:

- **P1.3, the golden master,** is generated from the tag, not from the working tree: check
  `python-engine-final` out in a separate worktree, run `harness/golden_digest.py` and the corpus there,
  and commit the digests. The experiment's harness reads `backend/app/`, which only exists in that
  worktree.
- **P2.2, "CI runs the `.feature` files twice,"** does not apply: behave no longer runs on `develop`.
  G2 stays: 54/54 on cucumber-js, and the `(k − 1)/N` mutant fails 8 scenarios there too.
- **Until P1.1 there is no test suite on `develop`.** The pre-push hook is a no-op and the `.feature`
  files are not executed. The risk is that a scenario is edited without being run; the mitigation is that
  phase 1 starts next and that no scenario may change before G2 except for a bug found by the port.
- **P3.2** shrinks to what is left: rewrite the READMEs for Node and mark `api-contract.md` and the
  Connect decision as superseded. The tag is already pushed.
- **The tag is on the commit of 2026-11-09, not on a final one.** It is moved (force-pushed, with the
  owner's approval) only if the retired engine gets a fix.

## Consequences

- Milestone 5 stops at 5.4: the service definition exists in history (tag) and informs the field table.
  Tasks 5.5–5.17, milestone 7 and user stories US-12 and part of US-13 are dropped.
- A public API is a goal without a date. When it comes, the same TypeScript engine can run on Node
  behind Connect, so the figures stay identical.
- The documents of the retired stack stay as history. They describe `backend/` paths that exist only in
  the tag.

## Not decided here

- Hosting and analytics (D2, US-10): a static host, and a privacy-friendly counter or none.
- Whether live INCC (milestone 9) can be fetched from the browser (CORS on the Banco Central's SGS API).
- The wording of the disclaimer (D1) and the interface language decision (6.12).
