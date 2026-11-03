# Roadmap

Each milestone number links to its task breakdown in [tasks.md](tasks.md).

| # | Milestone | Status |
|---|---|---|
| [1](tasks.md#m1-gherkin-feature-files) | Gherkin feature files describing the business scenarios (`backend/features/`) | ✅ |
| [2](tasks.md#m2-python-engine-and-cli) | Workable Python engine + CLI | ✅ |
| [3](tasks.md#m3-bdd-validation) | BDD validation with **behave** (Allure labels); Portuguese feature files as documentation | ✅ |
| [4](tasks.md#m4-mvc-backend) | **MVC** backend: `app/models`, `app/views`, `app/controllers` | ✅ |
| [5](tasks.md#m5-flask-api) | Flask API controller, to the contract in [docs/api-contract.md](docs/api-contract.md): simulations as resources (`POST /api/simulations`, `GET /api/simulations/{id}[/path]`), `GET /api/fields`, comparisons (`GET`/`POST /api/comparisons`), what-ifs (`…?relative_to=`, `POST /api/simulations/{id}/what-if`), cash ladder (`POST /api/simulations/{id}/cash-ladder`); API-level behave features through an `HttpGateway` | 📝 contract specified |
| [6](tasks.md#m6-react-front-end) | React + TypeScript front-end (Vite) with Plotly: input form, cost breakdown, timeline stacked bars, SAC vs PRICE, comparison table, cash ladder | ⬜ |
| [7](tasks.md#m7-docker) | Docker: `docker-compose` with backend, frontend (nginx), behave test service | ⬜ |
| [8](tasks.md#m8-ui-acceptance-tests) | UI acceptance tests: behave + Playwright against the running stack | ⬜ |
| [9](tasks.md#m9-extensions) | Extensions: live INCC (FGV), TR on the bank phase, MIP/DFI insurance + admin fee, physical progress at signing (`docs/future-features/`), pro-soluto with interest, PDF/CSV export | ⬜ |

## Decisions taken (open questions from the handoff)

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
- **Validation at the API boundary**: `400` when the body cannot become a simulation input
  (shape, types, unknown fields — the controller's job, as argparse is for the CLI); `422` when the
  model rejects it (`SimulationError`, message verbatim, the same text the CLI prints).
