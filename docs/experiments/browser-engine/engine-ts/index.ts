/** The TypeScript port of the SINCERO engine (app/models + app/views/json_view). */
export { FIELDS, InputShapeError, SimulationError, inputFromDict } from "./inputs.js";
export type { FieldSpec, FlatInput, SimulationInput } from "./inputs.js";
export { simulate } from "./model.js";
export { cashLadder, cashLadderDict, compareDicts, simulateDict, simulationToDict, summaryToDict, whatIf } from "./view.js";
export type { Payload, Summary, WhatIfPayload } from "./view.js";
export { pyMoney, pySum } from "./pyfloat.js";
