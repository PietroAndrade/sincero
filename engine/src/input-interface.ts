/**
 * The behavioural contract of a simulation input (input_interface.py): the two things the
 * application DOES with an input, and nothing else. No data and no accessors: the data lives in
 * the DTOs (input-dto.ts), which every model component receives directly.
 */
import type { FlatInput } from "./input-dto.js";

export interface SimulationInputInterface {
  /** Throw `SimulationError` if the input describes an impossible contract; return the input otherwise. */
  validate(): SimulationInputInterface;
  /** A copy with some fields changed (any field of any DTO): the basis of every what-if. */
  withOverrides(overrides: FlatInput): SimulationInputInterface;
}
