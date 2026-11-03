# SINCERO — Off-plan apartment cost simulator (Brazil)

**Simulador de Impacto do INCC no Custo pela Evolução Real da Obra**

🇧🇷 [Versão em português](README.pt-br.md)

SINCERO shows the real cost of buying an apartment *na planta* in Brazil: the INCC
correction on everything you still owe during construction, the construction interest
charged by the bank, the closing costs, the SAC/PRICE installments after key handover,
the credit gap at transfer ("the Caixa trigger") — and what changes when you put more
cash on the table.

> Example: a R$ 440,000 apartment delivered in 19 months, 20% down payment, R$ 13,000 of
> FGTS at signing → R$ 86,155 (19.6%) on top of the list price before the first bank
> installment, and the bank must approve R$ 39,802 more than it pre-approved.

## Project layout

```
.
├── backend/                  Python (MVC) — models, views, controllers, behave suite
│   ├── app/models/           domain model (pure Python)
│   ├── app/views/            JSON payload (API / front-end contract) and text report
│   ├── app/controllers/      CLI today; Flask API in milestone 5
│   ├── features/             executable specification (Gherkin, English) + behave steps
│   ├── features_pt_br/       the same scenarios in Portuguese — documentation only, not executed
│   ├── support/              behave support library (no behave imports)
│   └── tests/                pytest unit tests
├── docs/                     design notes and future features
└── ROADMAP.md                milestones and decisions
```

## Running the application

Requirements: Python 3.11+.

```bash
cd backend
pip install -r requirements-dev.txt        # runtime + behave + pytest
```

### Command line (available now)

```bash
# The five reference properties (SO, F, SV, F4, RA) with 20% down payment and R$ 13,000 FGTS
python cli.py

# One property: price, months REMAINING until delivery, FGTS, monthly installment to the developer and
# the months with a balloon payment — the balloon AMOUNT is derived, never typed in
python cli.py --name RA --price 440000 --months 19 --fgts 13000 \
              --installment 2500 --balloon-month 6 --balloon-month 12

# "More cash" simulation: the same contract with increasing cash at signing
python cli.py --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000

# Closing costs, income ceiling and pro-soluto term
python cli.py --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35 --pro-soluto-months 24

# Full JSON payload (the same shape the API and the front-end will use)
python cli.py --price 440000 --months 19 --json

python cli.py --help                        # every option (INCC, bank rate, term, ITBI, pre-approved credit…)
```

Every option:

| Option | Meaning | Default |
|---|---|---|
| `--price`, `--months` | list price and **months remaining until delivery** (time left, not the project's total duration) | required |
| `--down-payment-pct` | down payment required by the developer (% of price) | 20 |
| `--fgts`, `--cash` | paid at signing; excess above the down payment reduces the financed balance | 0 |
| `--installment` | monthly amount paid to the developer during construction | balance ÷ months |
| `--balloon-month` | construction month with a balloon (repeatable); amount = uncovered balance ÷ balloons | none |
| `--incc`, `--bank-rate` | INCC and bank rate (% per year) | 7.0, 10.26 |
| `--term` | bank financing term (months) | 360 |
| `--itbi`, `--registry` | ITBI and registry/deed costs (% of price) | 2.0, 0.5 |
| `--income-ratio` | max share of household income the bank accepts as installment (0–1) | 0.30 |
| `--pre-approved` | credit pre-approved by the bank at signing | nominal balance |
| `--pro-soluto-months` | months to pay the developer any credit gap | 12 |

Defaults are defined once, in `backend/proto/sincero/simulation_input.proto`, from which the model's input DTOs (`ContractData`, `MarketData`, `BankCreditData`) are generated; `--help` prints them.

### API and web front-end

Planned: Flask API (milestone 5), React + TypeScript + Plotly front-end (milestone 6),
Docker Compose (milestone 7). See [ROADMAP.md](ROADMAP.md).

## Running the tests

```bash
cd backend
make features                     # behave — all business scenarios
make feature name=credit_gap      # one feature file
make tags tag=@more-cash          # a tag slice (@construction, @financing, @what-if, @validation…)
make unit                         # pytest — model invariants, view contract, support library
make test                         # both
make report                       # Allure 3 report (requires: npm install -g allure)
```

## Business model in one table

| Topic | Rule |
|---|---|
| Month numbering | 0 = signing; 1..N = the N months remaining until delivery; N = key handover; bank installments from N+1 |
| Rates | annual → monthly by compounding: `(1 + r)^(1/12) − 1` |
| Down payment | `price × pct`; FGTS + cash at signing deducted first; excess reduces the financed balance |
| Developer installments | buyer-chosen monthly amount (or balance ÷ N); each payment in month k × `(1 + INCC)^k` |
| Balloon payments | **derived**: `(remaining down payment − installment × N) ÷ number of balloon months`, INCC-corrected at their month |
| Mortgage balance | `price − max(down payment, upfront)`, × `(1 + INCC)^N` at delivery → "hidden INCC debt" |
| Construction interest | bank releases the balance evenly over the remaining months (k/N after month k); month k interest = corrected balance × k/N × bank rate; never amortizes. Physical progress at signing: [future feature](docs/future-features/physical-progress.md) |
| Closing costs | ITBI 2.0% + registry/deed 0.5% of the price (configurable) |
| Bank financing | SAC and PRICE over the term; minimum income = first installment ÷ 30% |
| Credit gap | `max(0, corrected balance − pre-approved)`; pro-soluto split linearly over the chosen months |

Details and the full step vocabulary: [`backend/features/README.md`](backend/features/README.md).
Technical layout of the backend: [`backend/README.md`](backend/README.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
