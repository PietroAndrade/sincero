# Why and how `SimulationInput` was split

A short summary. The full design, the bug table and the test inventory are in
[simulation-input-refactor.md](simulation-input-refactor.md).

## Why

`SimulationInput` used to be one frozen dataclass with sixteen fields and one `validate()`
method. That shape caused three concrete problems:

1. **Invisible validation gaps.** Half of the fields had no rule, and a missing rule looked
   exactly like a deliberate choice. The CLI crashed with Python tracebacks (`--incc -200`,
   `--bank-rate -100`) or printed nonsense with exit code 0 — a negative mortgage for
   `--down-payment-pct 150` or for FGTS + cash above the list price, negative closing costs for
   `--itbi -3`, a "pro-soluto R$ 0,00 x 0" next to a R$ 291 k credit gap.
2. **One bag for three unrelated things.** The property contract, the market conditions and the
   bank's position change for different reasons and at different times, yet every component
   received the whole sixteen-field object — `ClosingCosts` got the balloon months, `CreditGap`
   got the INCC rate.
3. **No contract.** Nothing stated what the application *does* with an input; the simulator and
   the what-if helpers depended on one concrete class.

## How

The class was split along the two axes where responsibilities actually differ — **what the data
is** and **what is done with it** — into four small modules under `backend/app/models/`:

| Module | Holds | Responsibility |
|---|---|---|
| `input_dto.py` | `ContractData`, `MarketData`, `BankCreditData` | **The data.** Frozen dataclasses with the application's defaults. Contract = the deal with the developer (price, months remaining, down payment, upfront FGTS/cash, installment and balloon months) and the amounts derived from it alone (`required_down_payment`, `upfront`, `remaining_down_payment`). Market = INCC, bank rate, term, ITBI, registry, income ratio. Bank credit = pre-approved credit and pro-soluto term. Field names are unique across the three, so a flat `field → value` map can be routed to its owner (`FIELD_OWNER`). |
| `input_interface.py` | `SimulationInputInterface` | **The behaviour.** A pure ABC with two abstract methods and nothing else — no attributes, no getters: `validate()` and `with_overrides()`. |
| `validators.py` | `Validator[T]`, seven validators, `CompositeValidator`, `ValidationPolicy` | **The rules.** One small class per concern, each typed on the single DTO it judges (`PropertyValidator`, `UpfrontPaymentsValidator`, `DeveloperPlanValidator` → `ContractData`; `MarketRatesValidator`, `FinancingValidator`, `ClosingCostsValidator` → `MarketData`; `BankCreditValidator` → `BankCreditData`). `DEFAULT_POLICY` chains them per DTO, in order, stopping at the first error so the user sees the most fundamental problem. |
| `inputs.py` | `SimulationInput` | **The composition.** `@dataclass(frozen=True)` with three fields — `contract`, `market`, `bank_credit` — and nothing hand-written (no `__init__`, `__slots__`, `__eq__`). It implements the interface: `validate(policy)` applies the policy to each DTO; `with_overrides(**fields)` builds a what-if copy across DTO boundaries. `from_dict` / `to_dict` convert to and from the flat form. |

And every model component now receives **only the DTO (or value) it needs**, wired in `simulator.py`:

```python
down_payment = DownPaymentPlan(contract, incc)
mortgage     = MortgageBalance(contract, incc)
construction = ConstructionInterest(mortgage, bank)          # months come with the mortgage
closing      = ClosingCosts(contract.list_price, market)
credit_gap   = CreditGap(bank_credit, mortgage)
total_cost   = TotalCost(contract.list_price, down_payment, mortgage, construction, closing)
```

Principles applied: **single responsibility** (a DTO stores and derives its own amounts, a
validator judges one DTO, the composition coordinates), **interface segregation** (a component
or validator sees only the data it uses; the interface promises only behaviour), **open/closed**
(a new rule is a new validator appended to the policy; a new field goes into the DTO that owns
it — nothing else changes), and **no anemic code** (no getters; `@dataclass` generates the
boilerplate).

## What did not change

- The **flat wire format**: the JSON `"input"` section, the CLI flags and the behave step
  dictionaries are the same. Grouping happens inside the model; `from_dict`/`to_dict` sit at the
  boundary (`json_view`, `cli_controller`).
- The **defaults** still live in the model (now in the DTOs) and the CLI still reads them for
  `--help`.
- Every **figure** of every pre-existing scenario. Only invalid inputs behave differently: they
  are rejected with a clear message and exit code 2 instead of crashing or misleading.

## New rules that came with the split

Down payment percentage within 0–100; INCC above −100 % per year (negative INCC, i.e. deflation,
stays valid); bank rate not negative; closing-cost percentages not negative; pre-approved credit
not negative; pro-soluto term at least one month; FGTS + cash not above the list price (exactly the
list price is a cash purchase and stays valid). Each has an isolated validator test on its DTO, an
end-to-end model test and a Gherkin scenario in `features/input_validation.feature` (mirrored in
Portuguese).
