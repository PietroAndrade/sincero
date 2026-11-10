# @sincero/engine

The SINCERO model and its JSON view in TypeScript: the engine that runs in the buyer's browser
([decision](../docs/decisions/engine-in-the-browser.md)). Pure computation, with no DOM, no Node and
no dependencies. `tsconfig.json` gives `src/` only the ES2022 library, so it cannot reach either by
accident. It is a port of the retired Python engine (`app/models` + `app/views/json_view.py`) and
gives its figures to the bit. The [golden master](golden/README.md) is the proof.

```ts
import { inputFromDict, simulate, simulationToDict } from "@sincero/engine";

const result = simulate(inputFromDict({ name: "RA", list_price: 440_000, months_remaining: 19, fgts_upfront: 13_000 }));
result.creditGap.gap;               // 39802.29732781008
simulationToDict(result);           // the payload: input, rates, down_payment, …, timeline
```

## API

The input model follows the retired Python design ([simulation-input-split.md](../docs/simulation-input-split.md)):
the data, the behaviour and the rules are apart.

| | |
|---|---|
| `FIELDS`, `fieldNames()`, `fieldDefaults()` | The 16 input fields in order: `name`, `group` (`contract`, `market`, `bank_credit`), `default` (absent: required) |
| `ContractData`, `MarketData`, `BankCreditData` | **The data**: frozen DTOs with the defaults. Only the contract has behaviour, the amounts that follow from it alone: `requiredDownPayment`, `upfront`, `remainingDownPayment` |
| `SimulationInputInterface` | **The behaviour**: `validate()` and `withOverrides(flat)`, nothing else |
| `SimulationInput` | **The composition**: `new SimulationInput(contract, market?, bankCredit?)`, frozen. `validate(policy = DEFAULT_POLICY)`, `withOverrides(flat)` (any field of any DTO), `SimulationInput.fromDict(flat)`, `toDict()` |
| `Validator<T>`, `CompositeValidator`, `ValidationPolicy`, `DEFAULT_POLICY` | **The rules**: one validator per concern, each on the one DTO it judges; the policy chains them contract → market → bank credit and the first broken rule wins. A new rule is a new validator in the policy (`src/validators.ts`) |
| `inputFromDict(flat)`, `inputToDict(input)` | The flat form at the boundary (a form, a JSON body, a scenario) ↔ `SimulationInput`. An unknown or missing field throws `InputShapeError` |
| `simulate(input)` | Validates (the first broken rule throws `SimulationError`, message verbatim) and returns a `SimulationResult` |
| `SimulationError`: `code`, `fields`, `params`; `MESSAGES` | A rejection says what (`code`, one per cause: `SimulationErrorCode`), where (`fields`: input fields, or `amounts[i]`) and with which numbers (`params`). `MESSAGES[code](params)` is the English message, so a translation needs the code and the params only. `InputShapeError` has a `code` (`missing_fields`, `unknown_fields`, `balloon_months_not_a_list`) and `fields` too |
| `compare(inputs)`, `whatIf(base, [[label, overrides], …])`, `cashLadder(base, amounts)` | Several results side by side. A what-if's labels are unique: a repeated label is one variation. A cash ladder's amounts must be finite, not negative, not above the list price and increasing to the cent; the first one that is not is named (`cash_ladder_*` codes) and nothing is simulated |
| `simulationToDict`, `summaryToDict`, `comparisonToDict`, `whatIfToDict` | The JSON view: the same keys, order and values as the Python view |
| `simulateDict`, `compareDicts`, `cashLadderDict` | Flat input in, payload out, in one call |

`src/numerics.ts` holds the two pieces of arithmetic that make the figures Python's to the bit:
`compensatedSum` (CPython's `sum()`) and `formatAmount` (`f"{x:,.2f}"`, ties to even). Keep them.

## Tests

```bash
nvm use            # Node 24: see .nvmrc; the bit-exact check needs V8 >= 13.6
npm ci
npm test           # from the repository root: typecheck + every workspace's tests
```

| Test | What |
|---|---|
| `test/golden.test.ts` | Every case of the golden master gives the expected answer to the bit (456 cases, ~12 s) |
| `test/models.test.ts`, `test/validators.test.ts`, `test/views.test.ts` | The retired `test_models.py`, `test_validators.py` and `test_views.py`: the same 24 + 55 + 6 cases and assertions. Where an assertion was about Python itself (a frozen dataclass, an ABC), its TypeScript equivalent is used, and each file's header lists the replacements. The text report's test moved with the text view to `cli/test/cli.test.ts` |
| `test/errors.test.ts` | Structured errors (P1.5): every rejection of the golden master rebuilt from its `code` and `params`; one case per code with its `fields`; a Portuguese message from the params alone |
| `test/cash-ladder.test.ts` | The cash ladder's amount rules (P1.6), against backlog US-07 AC1-AC5 |
| `test/api.test.ts` | The public surface, imported by the package name; RA's headline figures |
| `golden/tools/update.ts` | `npm run golden:update [-- --dry-run]`: see [Changing the figures](#changing-the-figures) |

The type-level assertions (`expectTypeOf`, `@ts-expect-error`: the interface is pure, a validator
takes only its DTO) are checked by `npm run typecheck`, which `npm test` runs first. The pre-push
hook (`.githooks/pre-push`) runs `npm test`; `npm ci` points git at it.

## Changing the figures

The golden master holds the retired Python engine's answers to 456 cases (and, since P1.6, the intended changes to them). A refactor must leave them
all unchanged. A change to the figures (a new rule, a corrected rule, a new default) changes some of
them, and that change goes through a review:

1. **A scenario first.** The `.feature` files are the specification: a scenario describes the new
   behaviour (or the changed one) before the engine does it.
2. **Change the engine.** `npm test` now fails in `golden.test.ts` and lists the cases whose answer
   changed.
3. **Look before writing.** `npm run golden:update -- --dry-run` lists every changed case with what
   changed: the outcome (`ok` → `rejected`), the message, or the reply (a figure, a key, a label, a
   row). The list must be what the change explains, and nothing else.
4. **Write.** `npm run golden:update` rewrites only the changed lines of `golden/expected.json`.
   Commit it **with** the engine change and the scenario, in the same change, and review its diff as
   part of it: one line per case whose answer changed.
5. **New cases** for the new behaviour go at the end of `golden/corpus.json`, one per line, with the
   next `id` and a `note` saying what they pin. `golden:update` writes their first answer. Cases are
   never removed or renumbered: an id is a position.

The updater refuses to run on Node < 24 (its `**` would write last-bit differences) and never
touches the header of `expected.json` (the oracle, the `**` probes). Never update to make a
refactor pass: if a refactor changes an answer, the refactor is wrong.

## Layout

| File | Ported from |
|---|---|
| `src/errors.ts` | `errors.py` (and Python's `TypeError` for a malformed input: `InputShapeError`) |
| `src/input-dto.ts` | `input_fields.py`, `input_dto.py` (`FIELDS` replaces the retired `.proto`) |
| `src/input-interface.ts` | `input_interface.py` |
| `src/inputs.ts` | `inputs.py` |
| `src/validators.ts` | `validators.py` |
| `src/model.ts` | `rates`, `down_payment`, `mortgage`, `construction`, `closing_costs`, `amortization`, `credit_gap`, `total_cost`, `timeline`, `simulator` |
| `src/comparison.ts` | `comparison.py` |
| `src/view.ts` | `json_view.py` (`inputFromDict`, `inputToDict` included) |
| `src/numerics.ts` | CPython's `sum()` and `{:,.2f}` |

The code came from [the browser-engine experiment](../docs/experiments/browser-engine/): its `engine-ts/`
moved here, and its `pyfloat.ts` is `numerics.ts`.
