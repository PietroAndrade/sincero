# SINCERO backend

User-facing documentation (how to run the app, business model) lives in the root
[README.md](../README.md) (English) and [README.pt-br.md](../README.pt-br.md) (Portuguese).
This file covers the technical layout.

Off-plan (na planta) apartment cost engine for Brazil: INCC correction, construction
interest (juros de obra), SAC/PRICE bank financing, closing costs, credit gap, "more
cash" simulations and a month-by-month cash-flow timeline.

## Architecture (MVC)

```
backend/
├── app/
│   ├── models/                 # domain — pure Python, no I/O, no serialization
│   │   ├── input_dto.py        #   ContractData / MarketData / BankCreditData — frozen DTOs, the defaults
│   │   ├── input_interface.py  #   SimulationInputInterface — pure ABC (methods only): validate(), with_overrides()
│   │   ├── inputs.py           #   SimulationInput — frozen dataclass of the three DTOs
│   │   ├── validators.py       #   Validator[DTO] ABC, one small validator per concern, ValidationPolicy
│   │   ├── rates.py            #   annual -> monthly compounding
│   │   ├── down_payment.py     #   DownPaymentPlan (installments + derived balloons, INCC-corrected)
│   │   ├── mortgage.py         #   MortgageBalance (nominal vs corrected: the "hidden debt")
│   │   ├── construction.py     #   ConstructionInterest (juros de obra; LinearRelease over months remaining)
│   │   ├── closing_costs.py    #   ITBI + registry/deed
│   │   ├── amortization.py     #   SacSchedule / PriceSchedule
│   │   ├── credit_gap.py       #   the "Caixa trigger" and pro-soluto
│   │   ├── total_cost.py       #   cost breakdown
│   │   ├── timeline.py         #   CashFlowTimeline (month 0 .. N + term)
│   │   ├── simulator.py        #   OffPlanSimulator -> SimulationResult
│   │   └── comparison.py       #   compare(), what_if(), cash_ladder()
│   ├── views/
│   │   ├── json_view.py        # SimulationResult -> dict (the API / front-end contract)
│   │   └── text_view.py        # SimulationResult -> terminal report
│   └── controllers/
│       ├── cli_controller.py   # argparse -> models -> views
│       └── api_requests.py     # HTTP API shape layer: JSON body -> simulation inputs (400 rules, 422 pass),
│                               #   for POST /api/simulations, /comparisons, …/what-if, …/cash-ladder
│                               #   (Flask blueprint on top of it: milestone 5)
├── cli.py                      # entry point
├── features/                   # Gherkin business scenarios (English, executed) + behave hooks and thin steps
│   ├── environment.py
│   └── steps/
├── features_pt_br/             # Portuguese translation of the scenarios — documentation only, not executed
├── support/                    # behave support library (no behave imports): world, metrics, money, gateway
├── tests/                      # pytest: model invariants, view contract, support library
├── behave.ini  .allurerc.mjs  Makefile  pytest.ini
```

Dependency direction: `controllers → views → models`. Tests: `features/` drive the
models through the JSON view (so the suite also pins the payload contract);
`tests/` unit-test each layer.

## Run

```bash
pip install -r requirements-dev.txt

python cli.py                                                    # reference properties
python cli.py --price 440000 --months 19 --fgts 13000 \
              --installment 2500 --balloon-month 6 --balloon-month 12
python cli.py --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000
python cli.py --price 440000 --months 19 --json                  # full payload

make features                      # behave — all business scenarios
make feature name=credit_gap       # one feature
make tags tag=@more-cash           # a slice
make unit                          # pytest
make report                        # Allure 3 report (npm install -g allure)
```

## Using the models directly

```python
from app.models import ContractData, MarketData, SimulationInput, simulate, compare, cash_ladder
from app.views import simulation_to_dict, what_if_to_dict

inp = SimulationInput(ContractData("RA", 440_000, 19, fgts_upfront=13_000, developer_installment=2_500,
                                   balloon_months=(6, 12)),
                      MarketData(incc_rate_pa=7.0))     # MarketData() and BankCreditData() default when omitted
inp = SimulationInput.from_dict({"name": "RA", "list_price": 440_000, "months_remaining": 19})  # flat form (JSON/CLI)
inp.contract.list_price, inp.market.incc_rate_pa         # the DTOs; inp.contract.required_down_payment is derived
result = simulate(inp)
result.mortgage.hidden_incc_debt            # typed access
result.down_payment.nominal_balloon         # derived: (remaining − 2,500 × 19) / 2
simulation_to_dict(result)                  # JSON payload
what_if_to_dict(cash_ladder(inp, [0, 30_000, 100_000]))
```

Model assumptions and step vocabulary: [`features/README.md`](features/README.md).
