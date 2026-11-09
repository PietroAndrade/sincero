# Plan: port SINCERO to TypeScript, engine in the browser

Status: draft, 2026-11-08, for approval. Evidence:
[experiments/browser-engine](../experiments/browser-engine/) (a TypeScript port, bit-identical to
the Python engine on 1.79 M figures, 0.7–1.0 s to the first result on a throttled phone vs 47–53 s
for Python in the browser). Replaces the server half of [mvp.md](mvp.md) and
[backlog.md](backlog.md); the buyer stories stay.

## Goal and end state

A buyer opens a web page, in Portuguese or English, and gets the real cost, the credit gap and the
cash ladder, computed **in their browser**. No server runs SINCERO, and no input leaves the
device. One language in the repository:

```
sincero/
├── package.json          npm workspaces; Node ≥ 24 pinned (.nvmrc, "engines")
├── engine/               @sincero/engine: the model + JSON view, pure TypeScript, no DOM, no deps
│   ├── src/
│   ├── test/             unit tests (vitest), ported from backend/tests/
│   └── golden/           the Python engine's answers, frozen: inputs + bit digests (~34 KB)
├── features/             the .feature files, moved unchanged from backend/features/ (+ features_pt_br/)
│   ├── steps/ support/   cucumber-js step definitions and world, in TypeScript
├── web/                  the app: Vite + the engine, PT/EN (today's frontend/)
├── cli/                  `npx sincero --price 440000 --months 19` (the same flags as cli.py)
├── e2e/                  Playwright: the main path in a browser
└── docs/
```

What does **not** change: the business rules, the 54 scenarios (their text), the figures, the README
business table, the decision history.

## Principles

1. **Freeze the Python engine now.** No new behaviour in Python from the day this plan is accepted;
   a bug fix lands in both. Two moving engines is the main risk of a port.
2. **Keep the oracle after Python is gone.** Before deleting Python, commit its answers as a golden
   master: per corpus case, a SHA-256 over the exact bits of the reply (prototyped:
   [golden_digest.py/.mjs](../experiments/browser-engine/harness/golden_digest.py), 425/425 identical on
   Node 24, 34 KB). Later changes to the figures update it on purpose, in a reviewed diff, after a
   scenario describes the change.
3. **Bit-exact where it is a tool, to the cent where it is a promise.** Bit-exactness against
   CPython is how the port is proven, on a pinned engine (Node ≥ 24; Node 22's `**` differs in the last
   bit of ~10 % of powers). In users' browsers (Safari, Firefox, older Chrome) the promise is
   the business one: every figure to the cent.
4. **Spec first.** The `.feature` files stay the specification, and run against the TypeScript engine
   before Python is removed.
5. **Keep the speed.** The page is fast because it is small (12.9 KB of engine). A performance
   budget in CI keeps it that way.

## Decisions to take before starting

| # | Decision | Recommendation | Why |
|---|---|---|---|
| A | Python's end | **Retire after gate G2** (below), tag `python-engine-final` | Two engines cost every rule change twice; the golden master keeps the oracle |
| B | Protobuf | **Retire with Python**; the field table (names, groups, defaults, units, labels) becomes TypeScript | Protobuf paid off as a contract between two languages over a wire. With one language and no wire it is a second schema language and a generator to maintain. If a public API is wanted later, the same engine can run in Node |
| C | CLI | **Port to Node** (3 pts) | About 180 lines (cli_controller + text_view); keeps the README examples working and is handy for scripting |
| D | UI stack | **Vite + React** as planned (react + react-dom: 67 KB gzipped, measured). Charts: **not Plotly** (basic bundle: 386 KB gzipped, 30× the whole proof of concept); uPlot (21 KB) or Chart.js (69 KB), or SVG as in the proof of concept | React's ecosystem (i18n, forms, Playwright examples) matters more than its size, within the budget. Preact or plain TypeScript are smaller alternatives |
| E | Tests | **vitest** (unit, golden), **cucumber-js** (the features), **@playwright/test** (e2e); allure-cucumberjs if the Allure report is kept | The `.feature` files and their `{Money}`/`{Percent}`/`{Metric}` parameter types map directly to cucumber-js |
| F | Layout | **npm workspaces** as above | One `npm ci`, one `npm test`; the engine is a package the web, the CLI and the features import |

## Phases

Sizes are Fibonacci points on the backlog's scale (no velocity yet). The order is one developer's
critical path; **G** marks a gate that must pass before the next phase.

### Phase 0: Decide (3 pts)

| Item | Pts | Done when |
|---|---|---|
| P0.1 Decision record: "the engine runs in the browser, in TypeScript", superseding [api-protocol-and-language](../decisions/api-protocol-and-language.md) for the web path; decisions A–F answered; Python frozen | 2 | Recorded in `docs/decisions/`, linked from ROADMAP |
| P0.2 ROADMAP, mvp.md and backlog.md rewritten to this plan (see [the mapping](#what-happens-to-the-backlog)) | 1 | No dropped item left in "Now" |
| P0.3 *Optional:* publish the proof of concept on a free static host as a preview for 3–5 buyers | 1 | A link testers can open; feedback collected during the port |

### Phase 1: The engine package (15 pts)

| Item | Pts | Done when |
|---|---|---|
| P1.1 Workspace skeleton: root `package.json`, Node 24 pinned, strict `tsconfig`, vitest, `npm test`; the pre-push hook runs `make test` **and** `npm test` | 2 | A clean clone passes both |
| P1.2 Move `experiments/browser-engine/engine-ts` into `engine/src`; `pyfloat.ts` → `numerics.ts` (keep the compensated sum; it is also better arithmetic); a public API (`simulate`, `compare`, `whatIf`, `cashLadder`, `FIELDS`) | 2 | The experiment's `run_features.py --engine ts` passes 54/54 against the package |
| P1.3 Golden master: the corpus (recorded behave calls, reference properties, seeded random cases, every rule) and the Python engine's digests, generated once by a script and committed; a vitest test checks every digest | 3 | 100 % identical on Node 24; a planted naive `sum()` fails it |
| P1.4 Port the model's unit tests: `test_models.py` (12), `test_validators.py` (19), `test_views.py` (6) | 3 | Same cases, same assertions, green |
| P1.5 Structured errors: `SimulationError` carries `code`, `field` and `params` besides the English message (unchanged text: the scenarios pin it) | 3 | The UI can mark the field and say it in Portuguese (US-08 AC1–AC2) without parsing prose |
| P1.6 Cash-ladder amount rules in the engine: sorted, non-negative, not above the list price (were planned for the API's `CreateCashLadderRequest`) | 2 | US-07 AC4–AC5 testable on the engine |

**G1:** golden 100 % on Node 24; unit tests green; 54/54 through the package; a planted mutant fails.

### Phase 2: The specification in TypeScript (6 pts)

| Item | Pts | Done when |
|---|---|---|
| P2.1 cucumber-js runs the `.feature` files (moved, text unchanged): the world, metrics and money support (~230 lines) and the 29 step definitions (~220 lines) ported; `test_support.py` (10) ported | 5 | 54/54 |
| P2.2 Until Python is retired, CI runs the same `.feature` files twice: behave against Python, cucumber-js against TypeScript | 1 | Both green on every push |

**G2:** 54/54 on cucumber-js; the `(k − 1)/N` mutant fails 8 scenarios there too.

### Phase 3: Retire Python (7 pts)

Done right after G2, so the UI is built in a one-language repository.

| Item | Pts | Done when |
|---|---|---|
| P3.1 CLI in Node: the same flags, the text report, `--json`, `--cash-ladder`; `test_cli_controller.py` (5) ported | 3 | The README's CLI examples print the same figures |
| P3.2 Remove Python: an **annotated tag** `python-engine-final`, **pushed** (`git push origin python-engine-final`: tags are not pushed by default), then delete `backend/` (engine, controllers, `proto/`, `app/gen`, `tools/`, requirements, Makefile) and `frontend/src/gen`; pre-push → `npm test`; READMEs (EN/PT) rewritten for Node. The documents stay: `api-contract.md` and the Connect decision marked *superseded*, with the tag and [how to bring the contract back](#a-public-api-later) | 3 | No Python in CI; a fresh clone runs with `npm ci && npm test`; the tag is on the remote |
| P3.3 Golden update protocol: `npm run golden:update` writes the new digests; a change to the figures needs a scenario first and a reviewed digest diff | 1 | Written in `engine/README.md` |

### Phase 4: The web app (38 pts), milestone 6 reshaped

The buyer stories of [backlog.md](backlog.md) stay, with their criteria, except what a server
brought.

| Item | Pts | Change from the backlog |
|---|---|---|
| 6.12 Record the language decision; D1 disclaimer wording | 1 + 1 | — |
| 6.1 Scaffold (Vite + React, translation file) | 3 | — |
| P4.1 Engine integration: errors → field marks and PT/EN text from `code`/`params` | 2 | Replaces 6.2 "generated API client" (3) |
| US-01 … US-07 | 2 + 8 + 2 + 5 + 2 + 3 + 5 | — (US-02 AC6 "same id" becomes "same figures": there are no ids without a store) |
| US-08 Understand what went wrong | 2 (was 3) | AC3–AC5 (slow server, unreachable, rate-limited) disappear; "the engine failed to load" replaces them |
| P4.2 Performance budget in CI: initial JavaScript ≤ 150 KB gzipped, first result ≤ 2 s on the Lighthouse phone profile (reuse `harness/measure.py`) | 2 | New |

**G3** = the roadmap's milestone C: RA in the browser shows 19.6 % and R$ 39,802.30, in PT and EN.

### Phase 5: Prove the main path (12 pts), milestone 8

| Item | Pts | Change |
|---|---|---|
| 8.1 Playwright fixture | 2 | `@playwright/test` in TypeScript, no behave |
| 8.2 UI driver for the cucumber world | 3 | Was `UiGateway` in Python |
| US-09 The main path in a browser | 5 | — |
| P5.1 The golden corpus in Chromium, Firefox and WebKit, to the cent | 2 | New: the cross-browser check the experiment could not run |

### Phase 6: Ship (16 pts)

| Item | Pts | Change |
|---|---|---|
| D2 Hosting and domain | 2 | Now a static host (GitHub Pages, Netlify, Cloudflare Pages): free, no process to run |
| D3 Feedback channel | 1 | — |
| P6.1 CI pipeline: typecheck, vitest, golden, cucumber-js, Playwright, performance budget, build, deploy previews | 3 | Was "should have" |
| US-10 Count usage without tracking people | 3 | No server to count on: a privacy-friendly analytics service, or none (decide in D2) |
| US-11 Send feedback | 2 | — |
| US-13 Reach SINCERO on its public address | 3 (was 5) | AC4 (health endpoint, one worker) and AC5 (CORS) disappear; rollback = redeploy the previous build |
| Release checklist and notes | 2 | — |

## What happens to the backlog

| Backlog items | Points | Fate |
|---|---|---|
| 5.3c, 5.4 | 8 | Done; their work stays in history (tag) and informs the field table |
| 5.5–5.14 (rules in the `.proto`, server, store, RPCs, REST retirement, `ConnectGateway`) | 43 | **Dropped**: no server |
| 5.17 CORS, US-12 abuse protection | 4 | **Dropped**: nothing to protect |
| 7.1–7.3 Docker images and compose | 5 | **Dropped**: a static site needs no containers |
| 6.2 Generated API client | 3 | **Replaced** by P4.1 (2) |
| US-08, US-13 | 8 | **Shrunk** to 5 |
| 6.12, D1, 6.1, US-01–US-07, 8.1, 8.2, US-09, D2, D3, US-10, US-11, release | | **Kept** |
| P0–P3, P4.2, P5.1, P6.1 | | **New** (porting, proof, budget, CI) |

Remaining work: **97 points** in this plan, against 115 left in the current backlog (123 minus the
finished 5.3c and 5.4). The end state also has one language and no server to operate.

## Order

```
P0 ─▶ P1 ─G1─▶ P2 ─G2─▶ P3 ─▶ P4 ─G3─▶ P5 ─▶ P6 ─▶ launch
           └─ (optional) P0.3 preview, feedback flows in during P1–P3
```

Porting first (P1–P3, 28 points) keeps the period with two engines short, and the UI is then built
on the final engine in a single-language repository. The alternative, starting the UI right after G1
and porting the features later, gives users something sooner but keeps Python, behave and the
dual CI alive through M6. The optional preview (P0.3) gets early feedback without that cost.

## Risks

| Risk | Mitigation |
|---|---|
| A rule changes in one engine only during the transition | Python frozen at P0.1; transition kept to P1–P3; both suites in CI (P2.2) |
| The oracle disappears with Python | Golden digests committed before deletion (P1.3); `python-engine-final` tag |
| JavaScript engines disagree in the last bit (measured: Node 22 vs Node 24) | Node ≥ 24 pinned for the bit-exact gate; browsers checked to the cent (P5.1) |
| The page grows and loses its speed | Performance budget in CI (P4.2); no Plotly |
| Error messages are English prose | Codes and fields on `SimulationError` (P1.5) |
| The M5 work feels wasted | It is tagged and documented; see [A public API later](#a-public-api-later) |
| Live INCC (M9) needs data from the Banco Central | Unverified whether its SGS API allows browser calls (CORS). If not, a scheduled build bakes the latest index into the site. Research before M9 |
| Safari/Firefox behave differently (untested) | P5.1 before launch |

## A public API later

A public API is a goal, without a date. Until then the `.proto` files would be code nothing uses,
drifting from the engine with every new input (TR, MIP/DFI, physical progress…), so they leave
with Python and come back when the API is designed:

```bash
git show python-engine-final:backend/proto/sincero/simulation_input.proto   # read one file
git checkout python-engine-final -- backend/proto                          # restore them all
```

What to reuse then, and what to redesign:

| Piece | At the tag | For a public API |
|---|---|---|
| `simulation_input.proto` | The input fields, with groups, defaults and `buf.validate` rules | **Reuse**: update it to the fields of that day; the TypeScript field table is the reference |
| `simulation_result.proto` | The result, typed field by field, mirroring the JSON view | **Reuse**: the same check (a test comparing it with the view) applies to the TypeScript view |
| `simulations_service.proto` | Ids, a store, `FieldMask` reads: shaped by the UI's need to fetch parts of a 180 KB payload | **Redesign** for third parties (probably stateless: input in, result out) |
| `connect_errors.py`, `api-contract.md` rev. 7 | The error model (`BadRequest`, `ErrorInfo`), the transport rules | **Reuse the decisions**; the code is Python and would be rewritten |
| The server | Python `connectrpc` | **The same TypeScript engine** on Node with `@connectrpc/connect-node` (the mature Connect implementation, per the [decision](../decisions/api-protocol-and-language.md)). The figures stay identical because it is the same code |

## Verified for this plan

- The port passes the 54 scenarios in Chromium and matches CPython on 1,791,838 figures and every
  rejection message ([experiment](../experiments/browser-engine/README.md)).
- The golden digest format gives 425/425 identical cases on Node 24 (366/425 on Node 22), in 34 KB.
- `**` vs CPython on 200,000 seeded powers: Node 22 differs in 19,206; Node 24, Node 25 and
  Chromium 141 in none.
- Sizes, gzipped: react + react-dom 67 KB, Chart.js 69 KB, uPlot 21 KB, plotly.js basic 386 KB.
- Tools exist at these versions: @cucumber/cucumber 13.3, vitest 5.1, @playwright/test 1.64, vite 8.3,
  tsx 4.23, allure-cucumberjs 3.12.
