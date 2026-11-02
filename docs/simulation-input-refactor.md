# Refactor: `SimulationInput` as three DTOs behind a pure interface, validation in small validators

**Scope:** `backend/app/models/` (`input_dto.py`, `input_interface.py`, `inputs.py`, `validators.py`,
`__init__.py`, and the components that read inputs), the views and CLI controller at the flat ↔
grouped boundary, tests, and the `input_validation` feature.
**Behaviour of valid inputs:** unchanged — every pre-existing scenario and unit test passes with the
same figures; the JSON payload and the CLI flags are byte-for-byte the same.
**Behaviour of invalid inputs:** six classes of input that used to crash or to produce a nonsense
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

Everything that used to be valid still is, including the deliberate edge cases: `--incc -2`
(deflation), `--incc 0`, `--bank-rate 0`, `--down-payment-pct 0` and `--down-payment-pct 100`.

## The new shape

```
app/models/
├── input_dto.py         ContractData, MarketData, BankCreditData  — frozen DTOs, no behaviour, the defaults
├── input_interface.py   SimulationInputInterface                  — pure ABC, abstract methods only
├── validators.py        InputValidator ABC + 7 small validators + CompositeValidator
└── inputs.py            SimulationInput                           — immutable composition of the three DTOs
```

```
   DTOs (input_dto.py)                SimulationInputInterface (ABC, methods only)      InputValidator (ABC)
   ───────────────────                ────────────────────────────────────────────      ────────────────────
   ContractData    ◄───────────────── contract()        -> ContractData                 validate(inp) -> None
   MarketData      ◄───────────────── market()          -> MarketData                            ▲
   BankCreditData  ◄───────────────── bank_credit()     -> BankCreditData        ┌───────────────┼──────────────┐
                                      required_down_payment() -> float           │               │              │
                                      upfront()               -> float    PropertyValidator  …  BankCreditValidator
                                      remaining_down_payment()-> float                           ▲
                                      validate()              -> self                            │
                                      with_overrides(**f)     -> copy                 CompositeValidator(validators)
                                                ▲                                                ▲
                                                │ implements                                     │
                                      SimulationInput(contract, market, bank_credit)             │
                                        .from_dict(flat) / .to_dict()                            │
                                        .validate(validator=None) ───── delegates ──── default_validator()
```

### The DTOs — `input_dto.py`

Three frozen dataclasses, one responsibility each, **data only** (a test asserts none of them
defines a public method):

| DTO | Responsibility | Fields |
|---|---|---|
| `ContractData` | what the buyer signs with the developer | `name`, `list_price`, `months_remaining`, `down_payment_pct`, `fgts_upfront`, `cash_upfront`, `developer_installment`, `balloon_months` |
| `MarketData` | the economic environment, independent of the property | `incc_rate_pa`, `bank_rate_pa`, `term_months`, `itbi_pct`, `registry_pct`, `income_commitment_ratio` |
| `BankCreditData` | the bank's position at signing and the fallback at delivery | `pre_approved_credit`, `pro_soluto_months` |

They carry the application's defaults — still the single source of truth the CLI reads for
`--help` (`field_defaults()`). `MarketData()` and `BankCreditData()` are fully defaulted, so the
common case is `SimulationInput(ContractData("RA", 440_000, 19))`.

Field names are unique across the three DTOs (asserted at import). `FIELD_OWNER` maps each name
to its DTO so a **flat** mapping — a JSON body, argparse flags, a what-if `{"incc_rate_pa": 4.0}` —
can be routed to the right group. That is what keeps the wire format, the CLI flags and the
behave step vocabulary unchanged while the model is grouped.

### `SimulationInputInterface` — `input_interface.py`

A *pure* interface: an `abc.ABC` whose every public member is an `@abstractmethod`, with **no
attributes and no annotations** (pinned by a test). It promises:

- the data, by responsibility: `contract()`, `market()`, `bank_credit()`;
- the derived amounts several components share: `required_down_payment()`, `upfront()`,
  `remaining_down_payment()`;
- the behaviour: `validate()` and `with_overrides(**fields)`.

Every component (`DownPaymentPlan`, `MortgageBalance`, `ConstructionInterest`, `ClosingCosts`,
`CreditGap`, `TotalCost`), the simulator, `compare`/`what_if`/`cash_ladder`, the views and the
validators are typed against this interface, not against `SimulationInput`. A test proves it by
feeding the validators a hand-rolled stub that implements only the interface. It also keeps the
imports acyclic: `validators.py` → interface → DTOs; `inputs.py` → all three.

### `SimulationInput` — `inputs.py`

No longer a dataclass with 16 fields: an immutable class (`__slots__`, `__setattr__` raises) that
**composes** the three DTOs and implements the interface.

```python
SimulationInput(contract: ContractData, market: MarketData = MarketData(), bank_credit: BankCreditData = BankCreditData())
SimulationInput.from_dict({"name": "RA", "list_price": 440_000, "months_remaining": 19, "incc_rate_pa": 4.0})
inp.to_dict()                       # the flat mapping back (inverse of from_dict)
inp.with_overrides(cash_upfront=30_000, incc_rate_pa=4.0)   # fields of different DTOs in one call
inp.validate()                      # default policy; inp.validate(my_validator) to substitute it
```

`from_dict` and `with_overrides` route each field through `FIELD_OWNER` and raise `TypeError` on
an unknown name. Equality, hash and `repr` follow the DTOs, so `input_from_dict(input_to_dict(x)) == x`
still holds.

### `validators.py` — one concern per class

Each validator reads **one DTO** through the interface (`inp.contract()`, `inp.market()` or
`inp.bank_credit()`):

| Validator | Reads | Rules |
|---|---|---|
| `PropertyValidator` | `contract()` | price > 0; months ≥ 1; **0 ≤ down payment % ≤ 100** (new) |
| `UpfrontPaymentsValidator` | `contract()` | FGTS and cash not negative |
| `DeveloperPlanValidator` | `contract()` | installment not negative; each balloon month in `1..months_remaining`; no repeats |
| `MarketRatesValidator` | `market()` | **INCC > −100 %** (new); **bank rate ≥ 0** (new) |
| `FinancingValidator` | `market()` | term ≥ 1; 0 < income ratio ≤ 1 |
| `ClosingCostsValidator` | `market()` | **ITBI and registry % not negative** (new) |
| `BankCreditValidator` | `bank_credit()` | **pre-approved credit not negative** (new); **pro-soluto term ≥ 1** (new) |

- Validators check the **shape** of the inputs. *Sizing* questions — "do these installments and
  balloons cover the balance?" — stay in `DownPaymentPlan`, which has the arithmetic; those
  messages are untouched.
- `CompositeValidator` runs in order and lets the **first** `SimulationError` propagate: one
  message (the behave suite asserts it verbatim) and a deterministic precedence when several
  fields are wrong — contract before market before bank credit.
- `DEFAULT_VALIDATORS` / `default_validator()` is the application policy; validators are
  stateless so the module-level instances are shared.
- INCC **may be negative** (construction-cost deflation happens); only ≤ −100 % is rejected
  because `(1 + r)^(1/12)` has no real value there. A bank rate may be 0 (PRICE already
  special-cases it) but not negative.

### The boundary: flat outside, grouped inside

| Place | Before | After |
|---|---|---|
| `json_view.input_to_dict` | `asdict(inp)` | `{**asdict(contract), **asdict(market), **asdict(bank_credit)}` — same flat object |
| `json_view.input_from_dict` | `SimulationInput(**data)` | `SimulationInput.from_dict(data)` |
| `cli_controller.input_from_args` | `SimulationInput(**data)` | `SimulationInput.from_dict(data)` |
| `cli_controller.model_defaults` | `fields(SimulationInput)` | `field_defaults()` from the DTOs |
| `summary_to_dict`, `text_view` | `r.input.name` | `r.input.contract().name` |
| `support/` (behave world, gateway) | flat dicts | **unchanged** |

The payload's `"input"` section could become nested (`{"contract": …, "market": …, "bank_credit": …}`)
to mirror the model; that is a contract change for the future API/front-end and was deliberately
not made here.

## Tests

- `tests/test_validators.py` (new, 52 tests): the interface is abstract, has **only abstract
  methods and no attributes**, and `SimulationInput` implements it; the DTOs are frozen, carry
  no behaviour, have unique field names and are routed by `FIELD_OWNER`; `from_dict`/`to_dict`
  round-trip and reject unknown fields; `with_overrides` crosses DTO boundaries and leaves the
  original untouched; equality/hash follow the DTOs; every validator rejects each of its rules
  **in isolation** (no simulation run) and accepts a valid contract; a validator reads only its
  own DTO; validators accept a stub implementation of the interface; boundary values are
  accepted; the composite stops at the first error and respects order; a custom policy can be
  injected.
- `tests/test_models.py`: six new parametrised cases (one per new rule) end-to-end through
  `simulate()`; immutability test extended to the composed object and its DTOs.
- `tests/test_cli_controller.py`: reads field names from the DTOs instead of `fields(SimulationInput)`.
- `features/input_validation.feature`: 10 new scenarios (42 → 52), all written with the existing
  step vocabulary — nothing added to `features/steps/`. They cover each new rule through the
  JSON-view gateway (pinning the API contract too) plus a positive scenario: a deflationary INCC
  is valid and yields a negative hidden debt. `features_pt_br/validacao_de_entradas.feature`
  mirrors them (documentation only, not executed).

```
make unit       104 passed
make features   10 features, 52 scenarios, 384 steps passed
```

## Adding a field or a rule from now on

- **A field**: add it to the DTO that owns that responsibility (with its default). `from_dict`,
  `to_dict`, `with_overrides`, the JSON input section and `--help` defaults pick it up
  automatically; add a flag to `FLAG_FIELDS` (a test fails until you do).
- **A rule**: add the `if … raise SimulationError(…)` to the validator that reads that DTO, or add
  a new `InputValidator` subclass and append an instance to `DEFAULT_VALIDATORS` (its position
  decides precedence). Add a row to `test_each_validator_rejects_its_own_field` and, if it is
  user-visible, an example to `features/input_validation.feature` (+ the Portuguese mirror).
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
- Components that need a single DTO (`ClosingCosts`, `CreditGap`) could take that DTO directly
  instead of the whole interface (interface segregation). They keep the uniform
  `(inp: SimulationInputInterface, …)` signature for now so the simulator's wiring stays
  one-shaped.
