# Refactor: `SimulationInput` as three DTOs behind a pure interface, validation in small validators

**Scope:** `backend/app/models/` (`input_dto.py`, `input_interface.py`, `inputs.py`, `validators.py`,
`__init__.py`, and the components that read inputs), the views and CLI controller at the flat ↔
grouped boundary, tests, and the `input_validation` feature.
**Behaviour of valid inputs:** unchanged — every pre-existing scenario and unit test passes with the
same figures; the JSON payload and the CLI flags are byte-for-byte the same.
**Behaviour of invalid inputs:** seven classes of input that used to crash or to produce a nonsense
report are now rejected with a clear message (see [What the CLI got wrong](#what-the-cli-got-wrong)).

## Why

`SimulationInput` (`app/models/inputs.py`) was one frozen dataclass with 16 fields doing three jobs:

1. **storing** every input and its default — property, market and bank data in one bag;
2. **deriving** the amounts several components share (`required_down_payment`, `upfront`,
   `remaining_down_payment`);
3. **validating** — one 20-line `validate()` with every rule inlined.

The third job is where the bugs were: the method covered 8 of the 16 fields and nothing in the
structure made the gaps visible. The first job is where the coupling was: every component, view
and test touched the same 16-field class, and there was no contract saying *what* an input must
provide, only a concrete class.

## What the CLI got wrong

Running the CLI with edge-case flags before the refactor:

| Command (`python cli.py --price 440000 --months 19 …`) | Before | After |
|---|---|---|
| `--incc -200` | **Python traceback** (`TypeError: '>' not supported between 'complex' and 'float'` — a rate below −100 % gives a complex monthly factor) | `error: INCC rate must be greater than -100% per year`, exit 2 |
| `--incc -100` | report with a zero mortgage (factor `0^k`) | same error as above |
| `--bank-rate -100` | **Python traceback** (`ZeroDivisionError` in the PRICE formula) | `error: bank interest rate must not be negative`, exit 2 |
| `--down-payment-pct 150` | report with a **negative** mortgage balance and negative construction interest | `error: down payment percentage must be between 0 and 100`, exit 2 |
| `--down-payment-pct -10` | report with a zero down payment | same error as above |
| `--itbi -3` / `--registry -1` | report with **negative** closing costs lowering the total | `error: closing cost percentages must not be negative`, exit 2 |
| `--pre-approved -1000` | silently accepted (gap computed against a negative credit) | `error: pre-approved credit must not be negative`, exit 2 |
| `--pro-soluto-months 0` | report saying `pro-soluto R$ 0,00 x 0` while showing a R$ 291 k credit gap | `error: pro-soluto term must be at least 1 month`, exit 2 |
| `--cash 500000` (or `--fgts 300000 --cash 200000`) | report with a **negative** mortgage balance (R$ −60 k), negative construction interest and a negative SAC installment | `error: upfront payments of R$ 500,000.00 exceed the list price of R$ 440,000.00`, exit 2 |

Everything that used to be valid still is, including the deliberate edge cases: `--incc -2`
(deflation), `--incc 0`, `--bank-rate 0`, `--down-payment-pct 0`, `--down-payment-pct 100` and
`--cash 440000` (FGTS + cash **equal** to the price is a cash purchase: mortgage, construction
interest and bank installments all R$ 0, only the closing costs remain).

## The new shape

```
app/models/
├── input_fields.py      ContractFields, MarketFields, BankCreditFields — GENERATED from proto/sincero/simulation_input.proto (make dto)
├── input_dto.py         ContractData, MarketData, BankCreditData  — frozen DTOs: the generated fields + derived amounts
├── input_interface.py   SimulationInputInterface                  — pure ABC: validate(), with_overrides()
├── validators.py        Validator[T] ABC, 7 validators, CompositeValidator, ValidationPolicy
└── inputs.py            SimulationInput                           — @dataclass(frozen=True) of the three DTOs
```

```
   DTOs (input_dto.py)                         Validators (validators.py)
   ───────────────────                         ──────────────────────────
   ContractData  ──── judged by ────►  PropertyValidator, UpfrontPaymentsValidator, DeveloperPlanValidator
     .required_down_payment                                    │
     .upfront                                                  ▼
     .remaining_down_payment           ValidationPolicy(contract=Composite[...],
   MarketData    ──── judged by ────►                   market=Composite[MarketRates, Financing, ClosingCosts],
   BankCreditData ─── judged by ────►                   bank_credit=Composite[BankCredit])
                                                               ▲
   SimulationInputInterface (ABC, methods only)                │
     validate()            ◄── implements ──  SimulationInput  │  (frozen dataclass)
     with_overrides()                           .contract      │
                                                .market        │
                                                .bank_credit   │
                                                .validate(policy=DEFAULT_POLICY) ─┘
                                                .with_overrides(**fields) / .from_dict() / .to_dict()
```

### The DTOs — `input_dto.py`

Three frozen dataclasses, one responsibility each:

| DTO | Responsibility | Fields |
|---|---|---|
| `ContractData` | what the buyer signs with the developer | `name`, `list_price`, `months_remaining`, `down_payment_pct`, `fgts_upfront`, `cash_upfront`, `developer_installment`, `balloon_months` — plus the derived `required_down_payment`, `upfront`, `remaining_down_payment` |
| `MarketData` | the economic environment, independent of the property | `incc_rate_pa`, `bank_rate_pa`, `term_months`, `itbi_pct`, `registry_pct`, `income_commitment_ratio` |
| `BankCreditData` | the bank's position at signing and the fallback at delivery | `pre_approved_credit`, `pro_soluto_months` |

The three derived amounts sit on `ContractData` because they depend on contract fields only
and are read by two components (`DownPaymentPlan`, `MortgageBalance`) and one validator
(`UpfrontPaymentsValidator`): the data that owns the formula exposes it once, as a property,
instead of an accessor on a wrapper. `MarketData` and `BankCreditData` have no behaviour (a
test pins both facts).

The DTOs carry the application's defaults — still the single source of truth the CLI reads for
`--help` (`field_defaults()`). `MarketData()` and `BankCreditData()` are fully defaulted, so the
common case is `SimulationInput(ContractData("RA", 440_000, 19))`. Field names are unique across
the three (asserted at import); `FIELD_OWNER` maps each name to its DTO so a **flat** mapping —
a JSON body, argparse flags, a what-if `{"incc_rate_pa": 4.0}` — can be routed to the right group.

### `SimulationInputInterface` — `input_interface.py`

A *pure* interface: an `abc.ABC` whose only members are two `@abstractmethod`s, with no
attributes, no annotations and no getters (pinned by a test). It promises what the application
**does** with an input — `validate()` and `with_overrides(**fields)` — and nothing about how the
data is stored. The data is reached as plain dataclass fields of the implementation.

### `SimulationInput` — `inputs.py`

```python
@dataclass(frozen=True)
class SimulationInput(SimulationInputInterface):
    contract: ContractData
    market: MarketData = MarketData()
    bank_credit: BankCreditData = BankCreditData()
```

`@dataclass` generates the constructor, equality, hash, repr and immutability; there is no
hand-written `__init__`, `__slots__`, `__eq__` or accessor. The class adds only what concerns the
three DTOs *together*:

- `validate(policy=DEFAULT_POLICY)` — applies `policy.contract` to `self.contract`,
  `policy.market` to `self.market`, `policy.bank_credit` to `self.bank_credit`, in that order,
  and returns `self` (`OffPlanSimulator` chains `inp.validate()`).
- `with_overrides(**fields)` — a copy with fields of any DTO changed, e.g.
  `inp.with_overrides(cash_upfront=30_000, incc_rate_pa=4.0)`; the basis of `what_if` and
  `cash_ladder`.
- `from_dict(flat)` / `to_dict()` — the flat form used by the JSON view and the CLI controller.
  Unknown field names are a `TypeError`.

### Components receive only the DTO they need

| Component | Before | After |
|---|---|---|
| `DownPaymentPlan` | `(inp, incc)` | `(contract, incc)` |
| `MortgageBalance` | `(inp, incc)` | `(contract, incc)` |
| `ConstructionInterest` | `(inp, mortgage, bank)` | `(mortgage, bank)` — the mortgage already knows its months |
| `ClosingCosts` | `(inp)` | `(list_price, market)` |
| `CreditGap` | `(inp, mortgage)` | `(bank_credit, mortgage)` |
| `TotalCost` | `(inp, dp, mortgage, construction, closing)` | `(list_price, dp, mortgage, construction, closing)` |
| `SacSchedule` / `PriceSchedule` | `(…, inp.term_months, inp.income_commitment_ratio)` | unchanged: `(…, market.term_months, market.income_commitment_ratio)` |

`OffPlanSimulator.run()` unpacks the three DTOs once and wires the components; no component
imports `SimulationInput` any more.

### `validators.py` — one concern per class, one DTO per validator

`Validator[T]` is a generic ABC: `validate(data: T) -> None`. Each concrete validator is typed
on the single DTO it judges, so it cannot read (or be confused by) anything else:

| Validator | DTO | Rules |
|---|---|---|
| `PropertyValidator` | `ContractData` | price > 0; months ≥ 1; **0 ≤ down payment % ≤ 100** (new) |
| `UpfrontPaymentsValidator` | `ContractData` | FGTS and cash not negative; **FGTS + cash ≤ list price** (new) |
| `DeveloperPlanValidator` | `ContractData` | installment not negative; each balloon month in `1..months_remaining`; no repeats |
| `MarketRatesValidator` | `MarketData` | **INCC > −100 %** (new); **bank rate ≥ 0** (new) |
| `FinancingValidator` | `MarketData` | term ≥ 1; 0 < income ratio ≤ 1 |
| `ClosingCostsValidator` | `MarketData` | **ITBI and registry % not negative** (new) |
| `BankCreditValidator` | `BankCreditData` | **pre-approved credit not negative** (new); **pro-soluto term ≥ 1** (new) |

- `CompositeValidator[T]` chains validators of the same DTO in order and lets the **first**
  `SimulationError` propagate: one message (the behave suite asserts it verbatim) and a
  deterministic precedence when several fields are wrong.
- `ValidationPolicy` is a frozen dataclass with one validator per DTO; `DEFAULT_POLICY` is the
  application's. A test or an API endpoint can pass its own policy to `validate()`.
- Validators check the **shape** of the inputs. *Sizing* questions — "do these installments and
  balloons cover the balance?" — stay in `DownPaymentPlan`, which has the arithmetic; those
  messages are untouched.
- INCC **may be negative** (construction-cost deflation happens); only ≤ −100 % is rejected
  because `(1 + r)^(1/12)` has no real value there. A bank rate may be 0 (PRICE already
  special-cases it) but not negative. FGTS + cash may **equal** the price (a cash purchase)
  but not exceed it.

### The boundary: flat outside, grouped inside

| Place | Before | After |
|---|---|---|
| `json_view.input_to_dict` | `asdict(inp)` | `inp.to_dict()` — same flat object |
| `json_view.input_from_dict` | `SimulationInput(**data)` | `SimulationInput.from_dict(data)` |
| `cli_controller.input_from_args` | `SimulationInput(**data)` | `SimulationInput.from_dict(data)` |
| `cli_controller.model_defaults` | `fields(SimulationInput)` | `field_defaults()` from the DTOs |
| `summary_to_dict`, `text_view` | `r.input.name` | `r.input.contract.name` |
| `support/` (behave world, gateway) | flat dicts | **unchanged** |

The payload's `"input"` section could become nested (`{"contract": …, "market": …, "bank_credit": …}`)
to mirror the model; that is a contract change for the future API/front-end and was deliberately
not made here.

## Tests

- `tests/test_validators.py` (new): the DTOs are frozen; only `ContractData` has behaviour, and
  only about its own amounts; field names are unique and routed by `FIELD_OWNER`; the interface
  is abstract and has **only two abstract methods, no attributes**; `SimulationInput` is a frozen
  dataclass of exactly the three DTOs with generated equality/hash; `from_dict`/`to_dict`
  round-trip and reject unknown fields; `with_overrides` crosses DTO boundaries and leaves the
  original untouched; every validator rejects each of its rules **in isolation, given only its
  DTO** (no `SimulationInput`, no simulation run) and accepts valid data; boundary values are
  accepted; the composite stops at the first error and respects order; the policy checks
  contract → market → bank credit; a custom policy can be injected.
- `tests/test_models.py`: seven new parametrised cases (one per new rule) end-to-end through
  `simulate()`; a cash-purchase test (upfront = price → zero mortgage, zero interest, zero
  installment); immutability via `FrozenInstanceError` on the composition and on a DTO.
- `tests/test_cli_controller.py`: reads field names from the DTOs instead of `fields(SimulationInput)`.
- `features/input_validation.feature`: new scenarios for every new rule, all written with the existing
  step vocabulary — nothing added to `features/steps/`. They cover each new rule through the
  JSON-view gateway (pinning the API contract too) plus two positive scenarios: a deflationary INCC
  is valid and yields a negative hidden debt; paying the whole price at signing is a cash
  purchase, not an error. `features_pt_br/validacao_de_entradas.feature`
  mirrors them (documentation only, not executed).

```
make test       # unit + features — everything green, figures of every pre-existing scenario unchanged
```

## Adding a field or a rule from now on

- **A field**: add it to the DTO that owns that responsibility (with its default). `from_dict`,
  `to_dict`, `with_overrides`, the JSON input section and `--help` defaults pick it up
  automatically; add a flag to `FLAG_FIELDS` (a test fails until you do). Pass it to the
  component that needs it — through the DTO it already receives, or as one more argument.
- **A rule**: add the `if … raise SimulationError(…)` to the validator of that DTO, or add a new
  `Validator[ThatDTO]` subclass and append an instance to the matching composite in
  `DEFAULT_POLICY` (its position decides precedence). Add a row to
  `test_each_validator_rejects_its_own_rule` and, if it is user-visible, an example to
  `features/input_validation.feature` (+ the Portuguese mirror).
- Nothing in `SimulationInput`, the interface, the simulator, the views or the CLI needs to change.

## Out of scope / follow-ups noticed

- `--cash-ladder abc` still dies with a `ValueError` traceback: that is argument parsing in
  `cli_controller.py`, not an input-model rule. A small `type=` function on the argparse flag
  would fix it.
- `CreditGap` keeps its `if pro_soluto_months > 0 else 0.0` guard. It is now unreachable through
  `simulate()` (the validator rejects 0) but harmless.
- `CompositeValidator` is fail-fast by design. If the future API wants to return *all* broken
  rules at once, a sibling that collects `SimulationError`s into a list is a ten-line addition
  and needs no change to the individual validators.
- `SimulationInputInterface` now has two methods and one implementation. It is the behavioural
  contract the first refactor asked for; if a second implementation never appears (e.g. a Flask
  request wrapper in milestone 5), it can be folded into `SimulationInput` without touching
  anything else.
