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
   bank's position changed for different reasons and at different times, yet every component,
   view and test was coupled to the same sixteen-field class.
3. **No contract.** Nothing stated what an input *must* provide; the simulator, the what-if helpers
   and the validators depended on one concrete class, so a request wrapper or a test stub could
   not stand in for it.

## How

The class was split along the two axes where responsibilities actually differ — **what the data
is** and **what is done with it** — into four small modules under `backend/app/models/`:

| Module | Holds | Responsibility |
|---|---|---|
| `input_dto.py` | `ContractData`, `MarketData`, `BankCreditData` | **Data only.** Frozen dataclasses with the application's defaults. Contract = the deal with the developer (price, months remaining, down payment, upfront FGTS/cash, installment and balloon months). Market = INCC, bank rate, term, ITBI, registry, income ratio. Bank credit = pre-approved credit and pro-soluto term. Field names are unique across the three, so a flat `field → value` map can be routed to its owner (`FIELD_OWNER`). |
| `input_interface.py` | `SimulationInputInterface` | **The contract.** A pure ABC with abstract methods only — no attributes: `contract()`, `market()`, `bank_credit()`, the derived amounts `required_down_payment()`, `upfront()`, `remaining_down_payment()`, and the behaviours `validate()` and `with_overrides()`. Everything downstream is typed against it. |
| `validators.py` | `InputValidator` + seven validators + `CompositeValidator` | **The rules.** One small class per concern, each reading a single DTO through the interface (`PropertyValidator`, `UpfrontPaymentsValidator`, `DeveloperPlanValidator` → contract; `MarketRatesValidator`, `FinancingValidator`, `ClosingCostsValidator` → market; `BankCreditValidator` → bank credit). `default_validator()` chains them in order and stops at the first error, so the user always sees the most fundamental problem. |
| `inputs.py` | `SimulationInput` | **The composition.** An immutable object built from the three DTOs (`SimulationInput(contract, market=MarketData(), bank_credit=BankCreditData())`). It implements the interface, derives the shared amounts, delegates `validate()` to the policy, and builds what-if copies with `with_overrides()` across DTO boundaries. `from_dict` / `to_dict` convert to and from the flat form. |

Principles applied: **single responsibility** (a DTO stores, a validator judges, the composition
coordinates), **interface segregation / dependency inversion** (components depend on the pure
interface, not on a class), **open/closed** (a new rule is a new validator appended to the
policy; a new field goes into the DTO that owns it — nothing else changes).

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
list price is a cash purchase and stays valid). Each has an isolated validator test, an end-to-end
model test and a Gherkin scenario in `features/input_validation.feature` (mirrored in Portuguese).
