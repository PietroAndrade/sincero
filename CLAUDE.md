# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SINCERO: a cost simulator for off-plan apartment purchases in Brazil (INCC correction, construction interest, closing costs, SAC/PRICE financing, the "Caixa trigger" credit gap). Only the Python backend (milestones 1–4) exists; the Flask API, React front-end and Docker are planned (see `ROADMAP.md`). `context.md` and `handoff-*.md` hold the original business context (Portuguese/English). The root `README.md` has the full business-rule table; update it and `README.pt-br.md` together.

Everything lives under `backend/` (Python 3.11+); run all commands from there.

## Commands

```bash
pip install -r requirements-dev.txt     # runtime + behave + pytest + allure-behave

make features                           # all behave scenarios
make feature name=credit_gap            # one feature file (features/<name>.feature)
make tags tag=@more-cash                # tag slice (@construction, @financing, @what-if, @validation…)
make unit                               # pytest (tests/)
make test                               # unit + features
make report                             # Allure 3 report (needs: npm install -g allure)

python -m pytest tests/test_models.py::test_name   # single pytest test
python cli.py --price 440000 --months 19 --json    # CLI; --help lists every option
```

No linter is configured.

## Architecture

MVC with a strict dependency direction `controllers → views → models`.

- `app/models/`: pure-Python domain, no I/O or serialization. `simulator.py` (`simulate(SimulationInput) -> SimulationResult`) composes the small models (`down_payment`, `mortgage`, `construction`, `closing_costs`, `amortization`, `credit_gap`, `total_cost`, `timeline`). `comparison.py` provides `compare()`, `what_if()`, `cash_ladder()`. Inputs: `input_dto.py` holds the three frozen DTOs and the defaults (`ContractData` — also derives `required_down_payment`/`upfront`/`remaining_down_payment` —, `MarketData`, `BankCreditData`); `input_interface.py` the pure, methods-only ABC (`SimulationInputInterface`: `validate()`, `with_overrides()`); `inputs.py` the frozen dataclass `SimulationInput(contract, market, bank_credit)` with `from_dict`/`to_dict` for the flat JSON/CLI form; `validators.py` the small `Validator[DTO]`s grouped per DTO in `DEFAULT_POLICY`. Components receive only the DTO they need (`DownPaymentPlan(contract, …)`, `ClosingCosts(list_price, market)`, `CreditGap(bank_credit, …)`). See `docs/simulation-input-refactor.md`. Validation errors are `SimulationError` (`errors.py`).
- `app/views/json_view.py`: `simulation_to_dict` / `input_from_dict` define the JSON payload, which is the contract for the future API and front-end. `text_view.py` renders the terminal report.
- `app/controllers/cli_controller.py`: argparse → models → views. `cli.py` is the entry point. The Flask API controller is milestone 5.

Domain rules that span several files (details in the root README table):
- Month 0 is signing, months 1..N are construction, N is key handover, and bank installments start at N+1.
- Annual rates become monthly by compounding, `(1+r)^(1/12)-1`, never by division.
- Balloon amounts are **derived** from the remaining down payment and the installment; they are never an input.
- Cash or FGTS at signing reduces the developer installment first. Only the excess reduces the financed balance.

## Testing structure

The business spec is Gherkin in `features/` (English, executed). `features_pt_br/` is a Portuguese translation kept as documentation only and is never run; keep it in sync by hand when you change a scenario.

- Step definitions in `features/steps/` stay thin. Logic lives in `support/` (world, `metrics`, `money`, `gateway`), which has no behave imports and is unit-tested in `tests/test_support.py`.
- Scenarios drive the models through `support/gateway.py::EngineGateway`, which goes via the JSON view. So the behave suite also pins the payload contract.
- `features/environment.py` builds the gateway once and resets the `SimulationWorld` before every scenario. Scenarios must pass alone and in any order. It also registers the custom step types `{x:Money}`, `{x:Percent}` and `{x:Metric}`.
- Step vocabulary and model assumptions: `backend/features/README.md`. Backend layout: `backend/README.md`.

`docs/reference/` keeps the early prototype scripts (`simulate-sac.py`, the empty `simulate-ballon-in-the-midle.py`); they are not part of the application.

## Standard commands

- `/finish-task` (`.claude/commands/finish-task.md`): test, push, PR, squash-merge on GitHub, then a new branch from `develop`. "finish task" means this command.
- Git hooks live in `.githooks/`. Enable them once per clone with `git config core.hooksPath .githooks`. `pre-push` blocks direct pushes to `develop`/`master` and runs `make test` (needs `backend/.venv`).
