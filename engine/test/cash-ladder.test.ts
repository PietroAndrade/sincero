/**
 * The cash ladder's amount rules (plan item P1.6), against backlog US-07 "See what more cash
 * changes". The rules are judged before anything is simulated: a refused ladder has no rows.
 * (The .feature files cannot change before G2, so these criteria are pinned here and in the golden
 * master's targeted cases #429-#433 and #450-#455 until a scenario describes them.)
 */
import { describe, expect, it } from "vitest";
import { SimulationError, cashLadder, inputFromDict, whatIfToDict } from "../src/index.js";
import { CashLadderValidator } from "../src/validators.js";

const RA = inputFromDict({ name: "RA", list_price: 440_000, months_remaining: 19, fgts_upfront: 13_000 });

function refusal(amounts: number[], base = RA): { code: string; fields: readonly string[]; message: string } {
  try {
    cashLadder(base, amounts);
  } catch (e) {
    if (e instanceof SimulationError) return { code: e.code, fields: e.fields, message: e.message };
    throw e;
  }
  throw new Error(`the ladder ${JSON.stringify(amounts)} was not refused`);
}

describe("US-07: what more cash changes", () => {
  it("AC1-AC2: RA's ladder: the installment reaches zero at 75,000, the gap moves only at 100,000", () => {
    const rows = whatIfToDict(cashLadder(RA, [0, 30_000, 75_000, 100_000])).scenarios.map((s) => s.summary);
    expect(rows.map((r) => r.developer_installment as number).map((x) => Math.round(x * 100) / 100)).toEqual([3947.37, 2368.42, 0, 0]);
    expect((rows[2]!.credit_gap as number).toFixed(2)).toBe("39802.30");
    expect((rows[3]!.credit_gap as number).toFixed(2)).toBe("36975.43");
  });

  it("AC4: unsorted amounts are refused, the first one out of order named", () => {
    expect(refusal([100_000, 0, 30_000])).toEqual({
      code: "cash_ladder_amounts_not_increasing",
      fields: ["amounts[1]"],
      message: "cash ladder amounts must increase: R$ 0.00 comes after R$ 100,000.00",
    });
    expect(refusal([0, 100_000, 50_000]).fields).toEqual(["amounts[2]"]);
  });

  it("AC4: a repeated amount is refused and named, also when only its cents repeat", () => {
    expect(refusal([0, 30_000, 30_000]).message).toBe("cash ladder amounts must increase: R$ 30,000.00 comes after R$ 30,000.00");
    expect(refusal([30_000.001, 30_000.004]).code).toBe("cash_ladder_amounts_not_increasing");
    expect(() => cashLadder(RA, [30_000, 30_000.01])).not.toThrow(); // a cent apart: two rows
  });

  it("AC4: a negative amount is refused and named", () => {
    expect(refusal([0, -1_000])).toEqual({
      code: "cash_ladder_amount_negative",
      fields: ["amounts[1]"],
      message: "cash ladder amount R$ -1,000.00 must not be negative",
    });
  });

  it("AC5: an amount above the list price is named as refused", () => {
    expect(refusal([0, 500_000])).toEqual({
      code: "cash_ladder_amount_above_list_price",
      fields: ["amounts[1]"],
      message: "cash ladder amount R$ 500,000.00 exceeds the list price of R$ 440,000.00",
    });
  });

  it("accepts an amount equal to the list price (a cash purchase); FGTS on top of it is the model's rule", () => {
    const noFgts = RA.withOverrides({ fgts_upfront: 0 });
    expect(whatIfToDict(cashLadder(noFgts, [0, 440_000])).scenarios[1]!.summary.balance_at_delivery).toBe(0);
    expect(refusal([0, 430_000]).code).toBe("upfront_above_list_price");
  });

  it("refuses what is not a finite number, by position", () => {
    expect(refusal([0, Number.NaN]).message).toBe("cash ladder amount #2 is not a finite number");
    expect(refusal([Number.POSITIVE_INFINITY]).fields).toEqual(["amounts[0]"]);
    expect(refusal(["30000" as unknown as number]).code).toBe("cash_ladder_amount_not_finite");
  });

  it("reports an invalid base before judging the amounts", () => {
    expect(refusal([-1], RA.withOverrides({ list_price: 0 })).code).toBe("list_price_not_positive");
  });

  it("still accepts an empty ladder: the base alone", () => {
    const w = cashLadder(RA, []);
    expect(w.variations).toEqual([]);
    expect(w.base.input).toBe(RA);
  });

  it("keeps the rules in a validator that needs only the amounts and the list price", () => {
    const rules = new CashLadderValidator();
    expect(() => rules.validate({ amounts: [0, 10, 20], list_price: 20 })).not.toThrow();
    expect(() => rules.validate({ amounts: [0, 21], list_price: 20 })).toThrow(SimulationError);
  });
});
