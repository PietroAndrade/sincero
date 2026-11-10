/**
 * The package's public surface, imported by its name as the web app, the CLI and the scenarios will
 * import it. The figures are RA's, the reference case of docs/plan/backlog.md (US-04, US-06); the
 * golden master pins every other figure.
 */
import { describe, expect, it } from "vitest";
import * as engine from "@sincero/engine";
import { FIELDS, InputShapeError, SimulationError, cashLadder, compare, inputFromDict, simulate, whatIf } from "@sincero/engine";

const RA = { name: "RA", list_price: 440_000, months_remaining: 19, fgts_upfront: 13_000 };

describe("@sincero/engine", () => {
  it("exports the inputs, the rules, the model and the view, and nothing else", () => {
    expect(Object.keys(engine).sort()).toEqual([
      "BankCreditData", "CompositeValidator", "ContractData", "DEFAULT_POLICY", "FIELDS", "InputShapeError",
      "MESSAGES", "MarketData", "SimulationError", "SimulationInput", "ValidationPolicy", "Validator",
      "cashLadder", "cashLadderDict", "compare", "compareDicts", "comparisonToDict",
      "fieldDefaults", "fieldNames", "formatAmount", "inputFromDict", "inputToDict", "monthTotal", "simulate", "simulateDict",
      "simulationToDict", "summaryToDict", "whatIf", "whatIfToDict",
    ]);
  });

  it("simulates RA: R$ 86,155 (19.6 %) on top of the list price, a credit gap of R$ 39,802.30", () => {
    const r = simulate(inputFromDict(RA));
    expect(r.totalCost.additional).toBeCloseTo(86_155.39, 2);
    expect(r.totalCost.extraPct).toBeCloseTo(19.58, 2);
    expect(r.creditGap.gap).toBeCloseTo(39_802.3, 2);
  });

  it("returns model results from compare, whatIf and cashLadder (views turn them into payloads)", () => {
    const ra = inputFromDict(RA);
    expect(compare([ra, ra]).map((r) => r.input.contract.name)).toEqual(["RA", "RA"]);
    const w = whatIf(ra, [["low INCC", { incc_rate_pa: 4.0 }]]);
    expect(w.variations[0]?.result.mortgage.hiddenInccDebt).toBeLessThan(w.base.mortgage.hiddenInccDebt);
    expect(cashLadder(ra, [0, 30_000]).variations.map((v) => v.label)).toEqual(["cash 0.00", "cash 30,000.00"]);
  });

  it("tells a rejected input from an input that is not one", () => {
    expect(() => simulate(inputFromDict({ ...RA, term_months: 0 }))).toThrow(SimulationError);
    expect(() => inputFromDict({ ...RA, list_prise: 1 })).toThrow(InputShapeError);
    expect(() => inputFromDict({ name: "x" })).toThrow(InputShapeError);
  });

  it("lists the 16 input fields in order, with their groups and defaults", () => {
    expect(FIELDS).toHaveLength(16);
    expect(FIELDS.filter((f) => f.default === undefined).map((f) => f.name)).toEqual(["name", "list_price", "months_remaining"]);
    expect(new Set(FIELDS.map((f) => f.group))).toEqual(new Set(["contract", "market", "bank_credit"]));
  });
});
