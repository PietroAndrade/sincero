# Roadmap

| # | Milestone | Status |
|---|---|---|
| 1 | Gherkin feature files describing the business scenarios (`backend/features/`) | ⬜ |
| 2 | Workable Python engine + CLI | ⬜ |
| 3 | BDD validation with **behave** (42 scenarios, Allure labels); Portuguese feature files as documentation | ⬜ |
| 4 | **MVC** backend: `app/models`, `app/views`, `app/controllers` | ⬜ |
| 5 | Flask API controller: `POST /api/simulate`, `/api/compare`, `/api/what-if`, `/api/cash-ladder`; API-level behave features | ⬜ |
| 6 | React + TypeScript front-end (Vite) with Plotly: input form, cost breakdown, timeline stacked bars, SAC vs PRICE, comparison table, cash ladder | ⬜ |
| 7 | Docker: `docker-compose` with backend, frontend (nginx), behave test service | ⬜ |
| 8 | UI acceptance tests: behave + Playwright against the running stack | ⬜ |
| 9 | Extensions: live INCC (FGV), TR on the bank phase, MIP/DFI insurance + admin fee, physical progress at signing (`docs/future-features/`), pro-soluto with interest, PDF/CSV export | ⬜ |

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
- **JSON payload**: `app/views/json_view.py::simulation_to_dict` is the API contract
  (`python backend/cli.py --price 440000 --months 19 --json`).
