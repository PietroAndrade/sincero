/**
 * The one place the scenarios talk to the application (support/gateway.py). The Givens
 * accumulate flat inputs; the gateway runs the engine and answers with the JSON view, the payload
 * the UI reads. A browser driver (plan item 8.2) will implement the same interface.
 */
import { SimulationError, compareDicts, simulateDict } from "@sincero/engine";
import type { FlatInput, Payload, Summary } from "@sincero/engine";

export interface Gateway {
  simulate(data: FlatInput): Payload;
  compare(rows: readonly FlatInput[]): Summary[];
  /** The error a business rule raises: the scenarios assert its message. */
  isRejection(error: unknown): error is Error;
}

export class EngineGateway implements Gateway {
  simulate(data: FlatInput): Payload {
    return simulateDict({ ...data });
  }

  compare(rows: readonly FlatInput[]): Summary[] {
    return compareDicts(rows.map((r) => ({ ...r })));
  }

  isRejection(error: unknown): error is SimulationError {
    return error instanceof SimulationError;
  }
}
