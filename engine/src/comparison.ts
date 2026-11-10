/**
 * Side-by-side runs: several properties, or one property under alternative assumptions (ported from
 * app/models/comparison.py). These return model results; view.ts turns them into payloads.
 */
import type { FlatInput } from "./input-dto.js";
import type { SimulationInput } from "./inputs.js";
import { simulate } from "./model.js";
import type { SimulationResult } from "./model.js";
import { formatAmount } from "./numerics.js";
import { CashLadderValidator } from "./validators.js";

export function compare(inputs: readonly SimulationInput[]): SimulationResult[] {
  return inputs.map((input) => simulate(input));
}

export interface Variation {
  readonly label: string;
  readonly overrides: FlatInput;
  readonly result: SimulationResult;
}

export interface WhatIf {
  readonly base: SimulationResult;
  readonly variations: readonly Variation[];
}

/**
 * Run `base`, then each labelled variation (overrides of any input fields) in order:
 *
 *     whatIf(ra, [["INCC 4%", { incc_rate_pa: 4.0 }], ["R$ 30k cash", { cash_upfront: 30_000 }]])
 *
 * Labels are unique, as the keys of the dict the Python engine took: a repeated label keeps its
 * first position and its last overrides (which is also what a `Map` does).
 */
export function whatIf(base: SimulationInput, variations: Iterable<readonly [string, FlatInput]>): WhatIf {
  const byLabel = new Map<string, FlatInput>(variations);
  const baseResult = simulate(base);
  return {
    base: baseResult,
    variations: [...byLabel].map(([label, overrides]) => ({
      label,
      overrides,
      result: simulate(base.withOverrides(overrides)),
    })),
  };
}

/**
 * The "more cash" simulation: the same contract with each amount as cash at signing, labelled
 * `cash 30,000.00`. The base is validated first (its own error wins), then the amounts
 * (CashLadderValidator: finite, not negative, not above the list price, increasing to the cent),
 * and only then is anything simulated.
 */
export function cashLadder(base: SimulationInput, amounts: readonly number[]): WhatIf {
  base.validate();
  new CashLadderValidator().validate({ amounts, list_price: base.contract.list_price });
  return whatIf(
    base,
    amounts.map((amount): [string, FlatInput] => [`cash ${formatAmount(amount)}`, { cash_upfront: amount }]),
  );
}
