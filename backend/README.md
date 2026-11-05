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
│   │   ├── input_fields.py     #   GENERATED from proto/ (make dto): ContractFields / MarketFields / BankCreditFields
│   │   ├── input_dto.py        #   ContractData / MarketData / BankCreditData — the DTOs: the generated fields + derived amounts
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
│   ├── controllers/
│   │   ├── cli_controller.py   # argparse -> models -> views
│   │   ├── api_requests.py     # REST shape layer (contract revision 6): JSON body -> simulation inputs (400 rules, 422 pass);
│   │   │                       #   retired when the Connect service lands — FieldSpec / UNITS / UPPER_BOUNDS still read from here
│   │   ├── connect_errors.py   # Connect errors (contract revision 7): SimulationError -> invalid_argument + ErrorInfo,
│   │   │                       #   buf.validate -> invalid_argument + BadRequest, unknown id -> not_found
│   │   └── connect_app.py      # asgi_app() / wsgi_app(): the generated apps with unknown JSON keys refused
│   └── gen/sincero/            # GENERATED from proto/ (make proto): *_pb.py messages (protobuf-py),
│                               #   simulations_service_connect.py — the Connect service (connectrpc)
├── proto/sincero/simulation_input.proto   # the input fields — names, types, defaults, nullable, group — one flat message
├── proto/sincero/simulation_result.proto  # the outputs: SimulationResult (simulation_to_dict) and Summary (summary_to_dict)
├── proto/sincero/simulations_service.proto  # the API: service Simulations, its requests and responses; states the contract revision
├── proto/google/rpc/error_details.proto     # vendored (googleapis): ErrorInfo, BadRequest — the error details
├── tools/gen_dto.py            # .proto -> app/models/input_fields.py (make dto; tests fail while they disagree)
├── tools/gen_proto.py          # proto/ -> app/gen/ + ../frontend/src/gen/ (make proto / proto-check; tests/test_gen_proto.py)
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

First-time setup (venv, `npm ci`) and how to check that everything works: [Verify](../README.md#verify) in the root README.

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
make dto                           # regenerate app/models/input_fields.py from proto/sincero/simulation_input.proto
make proto                         # regenerate app/gen/ (Python) and ../frontend/src/gen/ (TypeScript) from proto/sincero/*.proto
make proto-check                   # fail (with a diff) while the generated code and the .proto files disagree
```

## Adding or changing an input field

The fields of the input DTOs are declared once, in `proto/sincero/simulation_input.proto`
(one flat `SimulationInput` message; each field's `(sincero.field)` option names its owning
group, its default and whether `null` is a value). Edit the `.proto`, run `make dto`, commit
both: `tests/test_gen_dto.py` fails while `app/models/input_fields.py` and the `.proto`
disagree. `make dto` also needs `proto/buf_validate.binpb` (see `proto/README.md`). The CLI's `--help` and the API's `GET /api/fields` read the DTOs, so they follow.
What the `.proto` does not carry: the CLI flag and help text (`cli_controller.py`), the unit
and the API ceiling (`api_requests.py`), the model's validation rules (`validators.py`).

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
