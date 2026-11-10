/**
 * The JSON view (ported from app/views/json_view.py): the payload of a simulation
 * (`simulationToDict`), one comparison row (`summaryToDict`), a comparison and a what-if. Same keys,
 * same order, same values as the Python view: the scenarios read these objects.
 */
import { cashLadder, compare } from "./comparison.js";
import type { WhatIf } from "./comparison.js";
import { InputShapeError } from "./errors.js";
import type { FlatInput } from "./input-dto.js";
import { SimulationInput } from "./inputs.js";
import { PriceSchedule, SacSchedule, monthTotal, simulate } from "./model.js";
import type { AmortizationSchedule, SimulationResult } from "./model.js";

export type Payload = Record<string, unknown>;

/**
 * The input section of the payload: one flat object with every field of every DTO. The grouping
 * is a model concern; the wire format, the form and the scenarios stay flat.
 */
export function inputToDict(input: SimulationInput): FlatInput {
  return input.toDict();
}

/** Inverse of inputToDict, for whatever reads a request (a form, a scenario, a JSON body). */
export function inputFromDict(data: FlatInput): SimulationInput {
  // json_view.input_from_dict: `tuple(int(m) for m in data.get("balloon_months", ()))`
  const balloons = Object.hasOwn(data, "balloon_months") ? data.balloon_months : [];
  if (!Array.isArray(balloons))
    throw new InputShapeError("balloon_months must be a list of months", "balloon_months_not_a_list", ["balloon_months"]);
  return SimulationInput.fromDict({ ...data, balloon_months: balloons.map((m) => Math.trunc(Number(m))) });
}
export type Summary = Record<string, string | number>;

function scheduleToDict(s: AmortizationSchedule): Payload {
  const data: Payload = {
    first_installment: s.firstInstallment,
    last_installment: s.lastInstallment,
    total_interest: s.totalInterest,
    total_paid: s.totalPaid,
    min_income: s.minIncome,
    schedule: s.schedule.map((i) => ({ ...i })),
  };
  if (s instanceof SacSchedule) data.amortization = s.amortization;
  if (s instanceof PriceSchedule) data.installment = s.installment;
  return data;
}

export function simulationToDict(r: SimulationResult): Payload {
  const { downPayment: dp, mortgage, constructionInterest: ci, closingCosts: closing, creditGap: cg, totalCost: tc, timeline: tl } = r;
  return {
    input: inputToDict(r.input),
    rates: { incc_pm: r.incc.monthly, bank_pm: r.bank.monthly },
    down_payment: {
      required: dp.required,
      upfront: dp.upfront,
      remaining: dp.remaining,
      nominal_installment: dp.nominalInstallment,
      missing_amount: dp.missingAmount,
      nominal_balloon: dp.nominalBalloon,
      balloons: dp.balloons.map((b) => ({ ...b })),
      total_paid: dp.totalPaid,
      incc_correction: dp.inccCorrection,
      schedule: dp.schedule.map((p) => ({ ...p })),
    },
    mortgage: {
      nominal_balance: mortgage.nominal,
      corrected_balance: mortgage.corrected,
      hidden_incc_debt: mortgage.hiddenInccDebt,
    },
    construction_interest: { total: ci.total, schedule: ci.schedule.map((c) => ({ ...c })) },
    closing_costs: { itbi: closing.itbi, registry: closing.registry, total: closing.total },
    financing: { sac: scheduleToDict(r.sac), price: scheduleToDict(r.price) },
    credit_gap: {
      pre_approved: cg.preApproved,
      needed: cg.needed,
      gap: cg.gap,
      pro_soluto_months: cg.proSolutoMonths,
      pro_soluto_installment: cg.proSolutoInstallment,
    },
    total_cost: {
      list_price: tc.listPrice,
      additional: tc.additional,
      total: tc.total,
      extra_pct: tc.extraPct,
      breakdown: [...tc.lines, tc.totalLine].map((line) => ({
        component: line.component,
        base_value: line.base_value,
        additional: line.additional,
        final_value: line.base_value + line.additional,
      })),
    },
    timeline: {
      months: tl.months.map((m) => ({ ...m, total: monthTotal(m) })),
      peak_month: tl.peak.month,
      peak_total: monthTotal(tl.peak),
      construction_phase_total: tl.constructionPhaseTotal,
    },
  };
}

export function summaryToDict(r: SimulationResult): Summary {
  const contract = r.input.contract;
  return {
    name: contract.name,
    list_price: contract.list_price,
    months_remaining: contract.months_remaining,
    cash_upfront: contract.cash_upfront,
    developer_installment: r.downPayment.nominalInstallment,
    nominal_balloon: r.downPayment.nominalBalloon,
    incc_on_down_payment: r.downPayment.inccCorrection,
    hidden_incc_debt: r.mortgage.hiddenInccDebt,
    balance_at_delivery: r.mortgage.corrected,
    construction_interest: r.constructionInterest.total,
    closing_costs: r.closingCosts.total,
    sac_first_installment: r.sac.firstInstallment,
    sac_last_installment: r.sac.lastInstallment,
    price_installment: r.price.installment,
    min_income_sac: r.sac.minIncome,
    min_income_price: r.price.minIncome,
    credit_gap: r.creditGap.gap,
    total_cost: r.totalCost.total,
    extra_pct: r.totalCost.extraPct,
    peak_month: r.timeline.peak.month,
    peak_total: monthTotal(r.timeline.peak),
  };
}

export function comparisonToDict(results: readonly SimulationResult[]): Summary[] {
  return results.map(summaryToDict);
}

export interface WhatIfPayload {
  base: Summary;
  scenarios: { label: string; overrides: FlatInput; summary: Summary; delta: Record<string, number> }[];
}

/** Each variation's summary, and its difference from the base for every numeric figure. */
export function whatIfToDict(w: WhatIf): WhatIfPayload {
  const base = summaryToDict(w.base);
  return {
    base,
    scenarios: w.variations.map(({ label, overrides, result }) => {
      const summary = summaryToDict(result);
      const delta: Record<string, number> = {};
      for (const [k, value] of Object.entries(summary))
        if (typeof value === "number") delta[k] = value - (base[k] as number);
      return { label, overrides, summary, delta };
    }),
  };
}

// ----- flat input in, payload out: what a form, a scenario step or a script calls ---------------
export const simulateDict = (data: FlatInput): Payload => simulationToDict(simulate(inputFromDict(data)));
export const compareDicts = (rows: readonly FlatInput[]): Summary[] =>
  comparisonToDict(compare(rows.map((r) => inputFromDict(r))));
export const cashLadderDict = (data: FlatInput, amounts: readonly number[]): WhatIfPayload =>
  whatIfToDict(cashLadder(inputFromDict(data), amounts));
