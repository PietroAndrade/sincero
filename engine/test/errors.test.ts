/**
 * Structured errors (plan item P1.5): a rejection carries a code, the fields to blame and the
 * params of its message, so the UI can mark the field and say it in Portuguese without parsing the
 * English prose (backlog US-08 AC1-AC2). The English text is unchanged: the golden master pins it.
 */
import { describe, expect, it } from "vitest";
import { InputShapeError, SimulationError, cashLadder, inputFromDict, simulate } from "../src/index.js";
import { MESSAGES } from "../src/errors.js";
import type { SimulationErrorCode, SimulationErrorParams } from "../src/errors.js";
import { fieldNames } from "../src/input-dto.js";
import { corpus, run } from "./golden.js";
import { ra } from "./fixtures.js";

/** The error `run` throws (the test fails if it throws nothing). */
function caught(run: () => unknown): unknown {
  try {
    run();
  } catch (e) {
    return e;
  }
  throw new Error("expected an error, nothing was thrown");
}

/** The SimulationError a golden case ends in, if it ends in one. */
function rejectionOf(c: (typeof corpus)[number]): SimulationError | undefined {
  try {
    run(c);
  } catch (e) {
    if (e instanceof SimulationError) return e;
  }
  return undefined;
}

const codes = Object.keys(MESSAGES) as SimulationErrorCode[];
const isField = (f: string) => fieldNames().includes(f) || /^amounts\[\d+\]$/.test(f);

describe("structured errors", () => {
  const rejections = corpus.map(rejectionOf).filter((e): e is SimulationError => e !== undefined);

  it("build every message of the golden master from its code and params", () => {
    expect(rejections.length).toBeGreaterThan(100);
    for (const e of rejections) {
      expect(codes, e.message).toContain(e.code);
      expect(MESSAGES[e.code as SimulationErrorCode](e.params as never), `${e.code} ${JSON.stringify(e.params)}`).toBe(e.message);
      expect(e.fields.every(isField), `${e.code}: ${e.fields.join(", ")}`).toBe(true);
      expect(Object.values(e.params).every((v) => typeof v === "number"), e.code).toBe(true);
    }
  });

  it("are frozen: the UI cannot change what it was told", () => {
    const e = rejections[0]!;
    expect(Object.isFrozen(e.fields) && Object.isFrozen(e.params)).toBe(true);
  });

  // One case per code: what a form needs to mark the field and rebuild the message.
  type Expectation = { [C in SimulationErrorCode]: [C, () => unknown, readonly string[], SimulationErrorParams[C]] }[SimulationErrorCode];
  const sim = (overrides: Record<string, unknown>) => () => simulate(ra.withOverrides(overrides));
  const ladder = (amounts: number[], overrides: Record<string, unknown> = {}) => () =>
    cashLadder(ra.withOverrides({ developer_installment: null, balloon_months: [], ...overrides }), amounts);
  const table: Expectation[] = [
    ["list_price_not_positive", sim({ list_price: 0 }), ["list_price"], { list_price: 0 }],
    ["months_remaining_below_one", sim({ months_remaining: 0, balloon_months: [] }), ["months_remaining"], { months_remaining: 0 }],
    ["down_payment_pct_out_of_range", sim({ down_payment_pct: 150 }), ["down_payment_pct"], { down_payment_pct: 150 }],
    ["upfront_negative", sim({ cash_upfront: -1 }), ["cash_upfront"], { fgts_upfront: 13_000, cash_upfront: -1 }],
    ["upfront_above_list_price", sim({ cash_upfront: 500_000 }), ["fgts_upfront", "cash_upfront"], { upfront: 513_000, list_price: 440_000 }],
    ["developer_installment_negative", sim({ developer_installment: -1 }), ["developer_installment"], { developer_installment: -1 }],
    ["balloon_month_after_delivery", sim({ balloon_months: [24] }), ["balloon_months", "months_remaining"], { month: 24, months_remaining: 19 }],
    ["balloon_month_below_one", sim({ balloon_months: [0] }), ["balloon_months"], { month: 0 }],
    ["balloon_months_repeated", sim({ balloon_months: [6, 12, 6] }), ["balloon_months"], { month: 6 }],
    ["balloons_without_installment", sim({ developer_installment: null }), ["developer_installment", "balloon_months"], {}],
    ["installments_exceed_balance", sim({ developer_installment: 5_000, balloon_months: [] }), ["developer_installment"], { covered: 95_000, remaining: 75_000 }],
    ["installments_leave_balance", sim({ balloon_months: [] }), ["developer_installment", "balloon_months"], { covered: 47_500, remaining: 75_000, missing: 27_500 }],
    ["incc_rate_too_low", sim({ incc_rate_pa: -100 }), ["incc_rate_pa"], { incc_rate_pa: -100 }],
    ["bank_rate_negative", sim({ bank_rate_pa: -1 }), ["bank_rate_pa"], { bank_rate_pa: -1 }],
    ["term_months_below_one", sim({ term_months: 0 }), ["term_months"], { term_months: 0 }],
    ["income_commitment_ratio_out_of_range", sim({ income_commitment_ratio: 1.5 }), ["income_commitment_ratio"], { income_commitment_ratio: 1.5 }],
    ["closing_cost_pct_negative", sim({ registry_pct: -1 }), ["registry_pct"], { itbi_pct: 2, registry_pct: -1 }],
    ["pre_approved_credit_negative", sim({ pre_approved_credit: -1 }), ["pre_approved_credit"], { pre_approved_credit: -1 }],
    ["pro_soluto_months_below_one", sim({ pro_soluto_months: 0 }), ["pro_soluto_months"], { pro_soluto_months: 0 }],
    ["cash_ladder_amount_not_finite", ladder([0, Number.NaN]), ["amounts[1]"], { index: 1 }],
    ["cash_ladder_amount_negative", ladder([-5]), ["amounts[0]"], { index: 0, amount: -5 }],
    ["cash_ladder_amount_above_list_price", ladder([0, 500_000]), ["amounts[1]"], { index: 1, amount: 500_000, list_price: 440_000 }],
    ["cash_ladder_amounts_not_increasing", ladder([0, 30_000, 30_000]), ["amounts[2]"], { index: 2, amount: 30_000, previous: 30_000 }],
  ];

  it("have one case per code in this table, and no code without one", () => {
    expect(table.map(([code]) => code).sort()).toEqual([...codes].sort());
  });

  it.each(table)("%s: the fields to mark and the params of the message", (code, run, fields, params) => {
    const e = caught(run) as SimulationError;
    expect(e).toBeInstanceOf(SimulationError);
    expect({ code: e.code, fields: e.fields, params: e.params }).toEqual({ code, fields, params });
    expect(e.message).toBe(MESSAGES[code](params as never));
  });

  it("mark both upfront fields when both are negative, and both closing costs", () => {
    expect((caught(sim({ fgts_upfront: -1, cash_upfront: -1 })) as SimulationError).fields).toEqual(["fgts_upfront", "cash_upfront"]);
    expect((caught(sim({ itbi_pct: -1, registry_pct: -1 })) as SimulationError).fields).toEqual(["itbi_pct", "registry_pct"]);
  });

  it("are enough to say the message in Portuguese (US-08 AC2), without reading the English", () => {
    const brl = (x: number) => x.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    const pt = { upfront_above_list_price: (p: SimulationErrorParams["upfront_above_list_price"]) =>
      `os pagamentos na assinatura, ${brl(p.upfront)}, passam do preço de tabela de ${brl(p.list_price)}` };
    const e = caught(sim({ cash_upfront: 500_000 })) as SimulationError;
    expect(e.code).toBe("upfront_above_list_price");
    expect(pt.upfront_above_list_price(e.params as SimulationErrorParams["upfront_above_list_price"]).replace(/\s/g, " "))
      .toBe("os pagamentos na assinatura, R$ 513.000,00, passam do preço de tabela de R$ 440.000,00");
  });

  it("let a custom validator reject with its own code, or none", () => {
    expect(new SimulationError("nope").code).toBe("rejected");
    expect(new SimulationError("nope", { code: "my_rule", fields: ["name"] }).fields).toEqual(["name"]);
  });
});

describe("shape errors", () => {
  it("name a required field left out (US-08 AC1: the form marks it as required)", () => {
    const e = caught(() => inputFromDict({ name: "RA", months_remaining: 19 })) as InputShapeError;
    expect(e).toBeInstanceOf(InputShapeError);
    expect([e.code, e.fields]).toEqual(["missing_fields", ["list_price"]]);
  });

  it("name unknown fields", () => {
    const e = caught(() => inputFromDict({ name: "RA", list_price: 1, months_remaining: 1, price: 1, colour: 2 })) as InputShapeError;
    expect([e.code, e.fields]).toEqual(["unknown_fields", ["colour", "price"]]);
  });

  it("refuse balloon months that are not a list", () => {
    const e = caught(() => inputFromDict({ name: "RA", list_price: 1, months_remaining: 1, balloon_months: null })) as InputShapeError;
    expect([e.code, e.fields]).toEqual(["balloon_months_not_a_list", ["balloon_months"]]);
  });
});
