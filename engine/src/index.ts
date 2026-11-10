/**
 * @sincero/engine: the SINCERO model and its JSON view. Pure TypeScript: no DOM, no Node, no
 * dependencies, so the same code runs in the browser, in the CLI and under the scenarios.
 *
 *     import { inputFromDict, simulate, simulationToDict } from "@sincero/engine";
 *     const payload = simulationToDict(simulate(inputFromDict({ name: "RA", list_price: 440_000, months_remaining: 19 })));
 *
 * Errors: `SimulationError` when a business rule rejects the input (the message is the one the
 * scenarios pin), `InputShapeError` when the input is not a simulation input at all (an unknown or
 * missing field). Both carry a `code` and the `fields` to blame; a SimulationError also carries the
 * `params` of its message, and `MESSAGES[code](params)` is its English text (a UI translates from
 * the code and the params, never from the English).
 */

export { InputShapeError, MESSAGES, SimulationError } from "./errors.js";
export type { ErrorDetails, InputShapeErrorCode, SimulationErrorCode, SimulationErrorParams } from "./errors.js";

// the inputs: the data (three DTOs), the behaviour (an interface), the composition, the rules
export { BankCreditData, ContractData, FIELDS, MarketData, fieldDefaults, fieldNames } from "./input-dto.js";
export type { BankCreditFields, ContractFields, ContractInit, FieldSpec, FlatInput, Group, MarketFields } from "./input-dto.js";
export type { SimulationInputInterface } from "./input-interface.js";
export { SimulationInput } from "./inputs.js";
export { CompositeValidator, DEFAULT_POLICY, ValidationPolicy, Validator } from "./validators.js";

// the model
export { monthTotal, simulate } from "./model.js";
export type { SimulationResult, TimelineMonth } from "./model.js";
export { cashLadder, compare, whatIf } from "./comparison.js";
export type { Variation, WhatIf } from "./comparison.js";

// the JSON view
export {
  cashLadderDict,
  compareDicts,
  comparisonToDict,
  inputFromDict,
  inputToDict,
  simulateDict,
  simulationToDict,
  summaryToDict,
  whatIfToDict,
} from "./view.js";
export type { Payload, Summary, WhatIfPayload } from "./view.js";

// `1,234.57`: two decimals, comma thousands, ties to even, as the model's messages print amounts
export { formatAmount } from "./numerics.js";
