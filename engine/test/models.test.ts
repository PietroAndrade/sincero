/**
 * Structural invariants of the domain model that the business features do not spell out.
 *
 * Ported from the retired tests/test_models.py (12 tests): same cases, same assertions.
 * Python's `FrozenInstanceError` is JavaScript's `TypeError` on assigning to a frozen object.
 */
import { describe, expect, it } from "vitest";
import { SimulationError, cashLadder, simulate, whatIf } from "../src/index.js";
import { monthTotal } from "../src/model.js";
import { compensatedSum } from "../src/numerics.js";
import { expectApprox } from "./approx.js";
import { ra } from "./fixtures.js";

const sum = (xs: number[]) => compensatedSum(xs);
const noPlan = { developer_installment: null, balloon_months: [] };

describe("the model", () => {
  it("ends the schedules with a zero balance", () => {
    const r = simulate(ra);
    expect(Math.abs(r.sac.schedule.at(-1)!.outstanding)).toBeLessThan(1e-6);
    expect(Math.abs(r.price.schedule.at(-1)!.outstanding)).toBeLessThan(1e-6);
    expect(r.sac.schedule).toHaveLength(360);
    expect(r.price.schedule).toHaveLength(360);
  });

  it("adds the amortizations up to the principal", () => {
    const r = simulate(ra);
    expectApprox(sum(r.sac.schedule.map((i) => i.amortization)), r.mortgage.corrected);
    expectApprox(sum(r.price.schedule.map((i) => i.amortization)), r.mortgage.corrected);
  });

  it("charges more interest with PRICE than with SAC", () => {
    const r = simulate(ra);
    expect(r.price.totalInterest).toBeGreaterThan(r.sac.totalInterest);
    expect(r.price.installment).toBeLessThan(r.sac.firstInstallment);
  });

  it("totals the timeline as the sum of its components", () => {
    const r = simulate(ra);
    const expected = r.downPayment.upfront + r.downPayment.totalPaid + r.constructionInterest.total + r.sac.totalPaid;
    expectApprox(sum(r.timeline.months.map(monthTotal)), expected);
  });

  it("adds the cost breakdown's base column up to the list price", () => {
    for (const inp of [ra, ra.withOverrides({ cash_upfront: 100_000, ...noPlan })]) {
      const r = simulate(inp);
      expectApprox(sum(r.totalCost.lines.map((line) => line.base_value)), inp.contract.list_price);
    }
  });

  it("runs each variation of a what-if", () => {
    const base = ra.withOverrides(noPlan);
    const w = whatIf(base, [["low incc", { incc_rate_pa: 4.0 }], ["more cash", { cash_upfront: 30_000 }]]);
    expect(w.variations.map((v) => v.label)).toEqual(["low incc", "more cash"]);
    expect(w.variations[0]!.result.mortgage.hiddenInccDebt).toBeLessThan(w.base.mortgage.hiddenInccDebt);
    expect(w.variations[1]!.result.downPayment.nominalInstallment).toBeLessThan(w.base.downPayment.nominalInstallment);
  });

  it("makes the cash ladder monotonic", () => {
    const w = cashLadder(ra.withOverrides(noPlan), [0, 30_000, 75_000, 100_000]);
    const installments = w.variations.map((v) => v.result.downPayment.nominalInstallment);
    const balances = w.variations.map((v) => v.result.mortgage.corrected);
    expect(installments).toEqual([...installments].sort((a, b) => b - a));
    expect(balances).toEqual([...balances].sort((a, b) => b - a));
  });

  it("keeps inputs immutable", () => {
    expect(() => {
      // @ts-expect-error: contract is readonly
      ra.contract = null;
    }).toThrow(TypeError);
    expect(() => {
      // @ts-expect-error: list_price is readonly
      ra.contract.list_price = 1;
    }).toThrow(TypeError);
  });

  it.each([
    ["term_months", 0, "financing term must be at least 1 month"],
    ["income_commitment_ratio", 0, "income commitment ratio must be between 0 and 1"],
    ["cash_upfront", -1, "upfront payments must not be negative"],
    ["balloon_months", [0], "balloon month 0 must be at least 1"],
    ["balloon_months", [6, 6], "balloon months must not repeat"],
    ["developer_installment", -1, "the monthly developer installment must not be negative"],
    // Rules added with the validator refactor: these used to crash or to produce a nonsense result.
    ["down_payment_pct", 150, "down payment percentage must be between 0 and 100"],
    ["incc_rate_pa", -100, "INCC rate must be greater than -100% per year"],
    ["bank_rate_pa", -1, "bank interest rate must not be negative"],
    ["itbi_pct", -3, "closing cost percentages must not be negative"],
    ["pre_approved_credit", -1000, "pre-approved credit must not be negative"],
    ["pro_soluto_months", 0, "pro-soluto term must be at least 1 month"],
    ["cash_upfront", 500_000, "upfront payments of R$ 513,000.00 exceed the list price of R$ 440,000.00"],
  ])("rejects %s = %j: %s", (field, value, message) => {
    const simulateIt = () => simulate(ra.withOverrides({ [field]: value }));
    expect(simulateIt).toThrow(SimulationError);
    expect(simulateIt).toThrow(message);
  });

  it("derives the balloons from the amount the installments leave uncovered", () => {
    const dp = simulate(ra).downPayment;
    expect(dp.balloons.map((b) => b.month)).toEqual([6, 12]);
    expectApprox(dp.missingAmount, 75_000 - 2_500 * 19);
    expectApprox(dp.nominalBalloon, 13_750);
    expectApprox(dp.nominalInstallment * 19 + dp.missingAmount, dp.remaining);
  });

  it("treats paying the whole price upfront as a cash purchase", () => {
    const r = simulate(ra.withOverrides({ fgts_upfront: 0, cash_upfront: 440_000, ...noPlan }));
    expect(r.mortgage.nominal === 0 && r.mortgage.corrected === 0).toBe(true);
    expect(r.constructionInterest.total === 0 && r.sac.firstInstallment === 0).toBe(true);
    expectApprox(r.totalCost.additional, r.closingCosts.total);
  });

  it("counts an installment rounded to the cent as covering the balance", () => {
    const r = simulate(ra.withOverrides({ developer_installment: 3_947.37, balloon_months: [] }));
    expect(r.downPayment.balloons).toEqual([]);
  });
});
