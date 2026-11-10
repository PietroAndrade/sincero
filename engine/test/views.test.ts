/**
 * The JSON view is the contract with the UI: shape, round trips and serialisability.
 *
 * Ported from the retired tests/test_views.py (6 tests): same cases, same assertions. "It is JSON"
 * (Python's `json.dumps` not raising) becomes "it survives JSON unchanged", because
 * `JSON.stringify` does not raise: it silently drops `undefined` and turns NaN into null. The text
 * report's test moved with the text view to the CLI (cli/test/cli.test.ts).
 */
import { describe, expect, it } from "vitest";
import { cashLadder, compare, comparisonToDict, inputFromDict, inputToDict, simulate, simulationToDict, whatIfToDict } from "../src/index.js";
import { expectApprox } from "./approx.js";
import { ra } from "./fixtures.js";

describe("the JSON view", () => {
  it("round-trips an input through its flat form", () => {
    const data = inputToDict(ra);
    expect(data.balloon_months).toEqual([6, 12]);
    expect(inputFromDict(data)).toStrictEqual(ra);
  });

  it("gives a simulation payload its shape, and it survives JSON", () => {
    const payload = simulationToDict(simulate(ra));
    expect(new Set(Object.keys(payload))).toEqual(
      new Set(["input", "rates", "down_payment", "mortgage", "construction_interest", "closing_costs", "financing", "credit_gap", "total_cost", "timeline"]),
    );
    const breakdown = (payload.total_cost as { breakdown: { component: string }[] }).breakdown;
    expect(breakdown.at(-1)!.component).toBe("Total");
    expect((payload.timeline as { months: unknown[] }).months).toHaveLength(1 + 19 + 360);
    expect(JSON.parse(JSON.stringify(payload))).toStrictEqual(payload);
  });

  it("names the rows of a comparison", () => {
    const f = ra.withOverrides({ name: "F", list_price: 396_000, months_remaining: 8, balloon_months: [4] });
    expect(comparisonToDict(compare([ra, f])).map((row) => row.name)).toEqual(["RA", "F"]);
  });

  it("gives a what-if's deltas relative to the base", () => {
    const out = whatIfToDict(cashLadder(ra.withOverrides({ developer_installment: null, balloon_months: [] }), [0, 30_000]));
    expectApprox(out.scenarios[0]!.delta.developer_installment!, 0);
    expect(out.scenarios[1]!.delta.developer_installment).toBeLessThan(0);
    expectApprox(out.scenarios[1]!.delta.hidden_incc_debt!, 0);
  });

  it("exposes the derived balloons in the payload", () => {
    const dp = simulationToDict(simulate(ra)).down_payment as { balloons: unknown; missing_amount: number };
    expect(dp.balloons).toEqual([
      { month: 6, nominal: 13_750.0 },
      { month: 12, nominal: 13_750.0 },
    ]);
    expect(dp.missing_amount).toBe(27_500.0);
  });
});
