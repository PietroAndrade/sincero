# Roadmap

Rewritten 2026-11-09 to the [TypeScript port plan](docs/plan/typescript-port.md): the engine runs in
the browser and there is no server ([decision](docs/decisions/engine-in-the-browser.md)). Items are
in [docs/plan/backlog.md](docs/plan/backlog.md). Milestones 1 to 4 are history; the numbers 5 to 9 of
the earlier plan are replaced by the phases below, and `tasks.md` (not tracked) still describes the
retired plan.

| Milestone | Scope | Status |
|---|---|---|
| 1 | Gherkin feature files describing the business scenarios (`features/`, moved from `backend/features/`) | ✅ |
| 2 | Python engine + CLI | ✅ retired, on `legacy/python-engine` and the tag `python-engine-final` |
| 3 | BDD validation with **behave** (Allure labels); Portuguese feature files as documentation | ✅ retired with Python; the `.feature` files stay |
| 4 | **MVC** backend: `app/models`, `app/views`, `app/controllers` | ✅ retired with Python |
| 5 | Connect API (task 5.4 reached: `service Simulations`, generated code) | ⛔ dropped after 5.4: no server ([decision](docs/decisions/engine-in-the-browser.md)) |
| P0 | Decide: the decision record (P0.1), plan documents rewritten (P0.2), optional preview (P0.3) | 🚧 P0.1, P0.2 done; P0.3 optional |
| P1 | The engine package `engine/`: workspace, golden master from the tag, unit tests, structured errors, cash-ladder rules → **G1** | ✅ P1.1–P1.6 done; **G1 passed 2026-11-09**: golden master 456/456 on Node 24 (bit-identical to Python except the 5 answers P1.6 changed on purpose), unit tests green, planted mutants fail, and 54/54 scenarios through the package in Chromium 155 (`run_features.py --engine ts`) |
| P2 | The `.feature` files on cucumber-js → **G2** | ✅ **G2 passed 2026-11-09**: 54/54 scenarios (399 steps) on cucumber-js against `@sincero/engine`, the text unchanged; the `(k − 1)/N` mutant fails 8 scenarios, as under behave; `test_support` ported (19 cases); Allure report kept (`npm run report`) |
| P3 | CLI in Node, READMEs for Node, golden update protocol | ✅ P3.1 `npx sincero`, the same flags and the same text as `cli.py` (17 recorded outputs of the Python CLI replayed, byte for byte); P3.2 READMEs (EN/PT) for Node, the API contract and the retired stack's decisions marked superseded; P3.3 `npm run golden:update` |
| P4 | Web app (Vite + React, PT + EN) → **G3**: RA in the browser shows 19.6% and R$ 39,802.30 | ⬜ |
| P5 | Playwright on the main path; the golden corpus in Chromium, Firefox and WebKit | ⬜ |
| P6 | Ship: static host, CI, usage counts or none, feedback, public address | ⬜ |
| 9 | Extensions: live INCC (FGV's index, republished by the Banco Central's SGS API) first, TR on the bank phase, MIP/DFI insurance + admin fee, physical progress at signing (`docs/future-features/`), pro-soluto with interest, PDF/CSV export | ⬜ after the launch |
| 7 | Docker | ⛔ dropped: a static site needs no containers |

## Decisions taken (open questions from the handoff)

- **The engine runs in the browser, in TypeScript; Python and protobuf are retired**
  ([decision](docs/decisions/engine-in-the-browser.md), accepted 2026-11-09; plan:
  [docs/plan/typescript-port.md](docs/plan/typescript-port.md)). This supersedes the Connect decision
  below for the web path, and milestones 5 (after 5.4) and 7 are dropped. The Python engine and the
  `.proto` files are on the branch `legacy/python-engine` and the tag `python-engine-final`. The
  milestone table and the plan documents were rewritten to it in P0.2 (2026-11-09).

- **Order of work** (2026-11-04, [docs/plan/prd.md](docs/plan/prd.md)): the UI (M6) starts as soon as the API
  runs over Connect with the behave suite passing over the wire (5.14). Playwright (M8) comes right
  after it, against the local processes, and Docker (M7) after that. The tool is public, with the
  interface in Portuguese and English.

- **Months** always mean *months remaining until delivery*, never the project's total duration.
- **Construction interest**: INCC-corrected balance × (k/N) × bank rate — the bank releases the balance
  evenly over the N months remaining. Physical progress at signing is documented as a future feature
  in `docs/future-features/physical-progress.md`.
- **Balloon payments**: the buyer chooses the monthly installment and the balloon months; the balloon
  amount is derived — `(remaining down payment − installment × N) / number of balloons` — and
  INCC-corrected at its month. Never an input.
- **More cash at signing**: reduces the developer installment first; once the down payment is fully
  covered, the excess reduces the financed balance (and therefore the bank installment).
- **JSON payload**: `app/views/json_view.py::simulation_to_dict` is the payload of a simulation
  (`python backend/cli.py --price 440000 --months 19 --json`). The API serves it whole at
  `GET /api/simulations/{id}/result` and **by node** at `GET /api/simulations/{id}/{path}` (the URL
  path is the JSON path), because 97 % of its 180 KB is three schedules a screen rarely needs
  at once.
- **API shape** ([docs/api-contract.md](docs/api-contract.md)): `POST` creates, `GET` reads, nothing
  is returned that was not asked for. A simulation's id is a hash of its resolved input, so
  creation is idempotent and a lost server state is recovered by re-posting. The four planned
  RPC routes (`/api/simulate`, `/api/compare`, `/api/what-if`, `/api/cash-ladder`) were replaced:
  - a **comparison** is a `GET` over stored simulations (`/api/comparisons?ids=…`), rows linking
    back to them; `POST /api/comparisons` creates the members and answers with that `GET`;
  - a **what-if** is a comparison with a reference row (`…&relative_to={id}`) — `overrides` and
    `delta` per row, no labels on the wire; `POST /api/simulations/{id}/what-if` derives the
    variations from a stored base ([decision](docs/decisions/what-if-as-comparison.md));
  - the **cash ladder** is a validated what-if preset (`POST /api/simulations/{id}/cash-ladder`,
    ascending non-negative amounts) whose response is the what-if's.
- **The API is a Connect RPC service, backend in Python, front-end in TypeScript**
  ([decision](docs/decisions/api-protocol-and-language.md), accepted 2026-11-03): one `.proto`
  generates the Python service and the browser client; Connect / gRPC-Web without a proxy;
  `buf.validate` rules replace the hand-written shape layer. The result is typed messages read with
  a `FieldMask`, and a failed model rule is `invalid_argument` with an `ErrorInfo` detail.
  `api-contract.md` revision 7 (2026-11-05) restates the contract as RPCs; the `.proto` files are the
  source and the document explains them.
- **A required input field has explicit presence**: `optional` + `(buf.validate.field).required`,
  so an absent field and an invalid one are refused with different violations, before the model runs
  ([decision](docs/decisions/required-fields-explicit-presence.md), accepted 2026-11-04). Applying it
  to `simulation_input.proto` is task 5.3c.
- **Input fields declared once, in protobuf**: `backend/proto/sincero/simulation_input.proto` is the
  source of truth for the input fields (names, types, defaults, nullable, owning DTO); the DTOs'
  fields are generated from it (`make dto`) and a test fails on drift. The `.proto` is a build-time
  schema only — the request path keeps the hand-written shape layer
  ([decision](docs/decisions/input-fields-from-proto.md)).
- **Validation at the API boundary**: `400` when the body cannot become a simulation input
  (shape, types, unknown fields — the controller's job, as argparse is for the CLI); `422` when the
  model rejects it (`SimulationError`, message verbatim, the same text the CLI prints).
