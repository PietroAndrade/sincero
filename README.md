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

The engine is TypeScript and runs **in the buyer's browser**: no server computes anything and no
input leaves the device ([decision](docs/decisions/engine-in-the-browser.md)). The same engine runs
the command line and the business scenarios. The web page is next ([ROADMAP.md](ROADMAP.md)).

## Project layout

```
.
├── engine/                   @sincero/engine — the model and its JSON view, pure TypeScript (no DOM, no dependencies)
│   ├── src/                  inputs, rules, model, comparison, view, structured errors
│   ├── test/                 unit tests, and the golden master's check
│   └── golden/               the retired Python engine's answers, frozen: 456 cases, compared to the bit
├── features/                 @sincero/features — the executable specification (Gherkin, English), run by cucumber-js
│   ├── steps/, support/      step definitions, the scenario world, money and metric parsing
│   └── pt_br/                the same scenarios in Portuguese — documentation only, not executed
├── cli/                      @sincero/cli — the command line, `npx sincero`
├── legacy/backend/           the retired Python engine: the golden master's oracle (also on the tag python-engine-final)
├── docs/                     decisions, plans, experiments, future features
└── ROADMAP.md                milestones and decisions
```

An npm workspace: one `npm ci`, one `npm test`.

## Getting started

Requirements: **Node.js 24** or newer (`.nvmrc`). Nothing else: no Python, no Docker, no server.

```bash
nvm use              # Node 24: the golden master is bit-exact on V8 >= 13.6, and npm refuses older Node
npm ci               # also points git at .githooks/ (the pre-push hook runs npm test)
npm test             # must exit 0
```

## Command line

```bash
# The five reference properties (SO, F, SV, F4, RA) with 20% down payment and R$ 13,000 FGTS
npx sincero

# One property: price, months REMAINING until delivery, FGTS, monthly installment to the developer and
# the months with a balloon payment — the balloon AMOUNT is derived, never typed in
npx sincero --name RA --price 440000 --months 19 --fgts 13000 \
            --installment 2500 --balloon-month 6 --balloon-month 12

# "More cash" simulation: the same contract with increasing cash at signing
npx sincero --price 440000 --months 19 --fgts 13000 --cash-ladder 0,30000,75000,100000

# Closing costs, income ceiling and pro-soluto term
npx sincero --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35 --pro-soluto-months 24

# Full JSON payload (the same object the web page will read)
npx sincero --price 440000 --months 19 --json

npx sincero --help                          # every option (INCC, bank rate, term, ITBI, pre-approved credit…)
```

Every option:

| Option | Meaning | Default |
|---|---|---|
| `--price`, `--months` | list price and **months remaining until delivery** (time left, not the project's total duration) | required |
| `--name` | label of the property | CUSTOM |
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
| `--cash-ladder` | comma-separated cash amounts, each not negative, not above the price, increasing | — |
| `--json` | the JSON payload instead of the text report | — |

Defaults are defined once, in the engine's field table (`FIELDS` in
[`engine/src/input-dto.ts`](engine/src/input-dto.ts)); `--help` prints them. Without `--price`, the
reference properties are shown. A rejected input prints `error: <message>` and exits with code 2, as
does a malformed command line (with a usage line on stderr). The report and the tables are those of
the retired Python CLI, character for character (`cli/test/fixtures/`).

## Running the tests

```bash
npm test                                       # typecheck + engine tests (golden master included) + CLI + every scenario
npm run features                               # cucumber-js — all business scenarios
npm run feature -- credit_gap.feature          # one feature file (path relative to features/)
npm run features -- --tags @more-cash          # a tag slice (@construction, @financing, @what-if, @validation…)
npm run report                                 # Allure 3 report in features/allure-report/
```

What each layer proves:

| Layer | Where | It fails when |
|---|---|---|
| Golden master | `engine/test/golden.test.ts` | any figure of 456 cases differs from the retired Python engine's, even in its last bit; a change to the figures goes through `npm run golden:update` ([protocol](engine/README.md#changing-the-figures)) |
| Unit tests | `engine/test/`, `cli/test/`, `features/test/` | a structural invariant, a rule, an error code or the CLI's output breaks |
| Business scenarios | `features/*.feature` | a figure of the specification is off by more than half a cent, or a message changes |

The pre-push hook (`.githooks/pre-push`, enabled by `npm ci`) runs `npm test`.

## Web page

Next: a static page (Vite + React), in Portuguese and English, with the engine inside it — no API,
nothing to host but files. Then Playwright on the main path in Chromium, Firefox and WebKit. See
[ROADMAP.md](ROADMAP.md) and the [plan](docs/plan/typescript-port.md).

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

Details and the full step vocabulary: [`features/README.md`](features/README.md). The engine, its API
and how to change the figures: [`engine/README.md`](engine/README.md). Documents:
[`docs/README.md`](docs/README.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
