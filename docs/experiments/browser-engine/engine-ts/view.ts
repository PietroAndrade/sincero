/**
 * Port of app/views/json_view.py and app/models/comparison.py: the payload of a simulation
 * (`simulation_to_dict`), one comparison row (`summary_to_dict`) and the what-if / cash ladder.
 * Same keys, same order, same values as the Python view — the behave suite reads these dicts.
 */
import { pyMoney } from "./pyfloat.js";
import { FlatInput, SimulationInput, inputFromDict, inputToDict, withOverrides } from "./inputs.js";
import { AmortizationSchedule, PriceSchedule, SacSchedule, SimulationResult, monthTotal, simulate } from "./model.js";

export type Payload = Record<string, unknown>;
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

// ----- comparison.py + what_if_to_dict -------------------------------------------------------------
export interface WhatIfPayload {
  base: Summary;
  scenarios: { label: string; overrides: FlatInput; summary: Summary; delta: Record<string, number> }[];
}

export function whatIf(base: SimulationInput, variations: [label: string, overrides: FlatInput][]): WhatIfPayload {
  const baseSummary = summaryToDict(simulate(base));
  return {
    base: baseSummary,
    scenarios: variations.map(([label, overrides]) => {
      const summary = summaryToDict(simulate(withOverrides(base, overrides)));
      const delta: Record<string, number> = {};
      for (const [k, value] of Object.entries(summary))
        if (typeof value === "number") delta[k] = value - (baseSummary[k] as number);
      return { label, overrides, summary, delta };
    }),
  };
}

/** The "more cash" simulation: the same contract with each amount as cash at signing. */
export function cashLadder(base: SimulationInput, amounts: number[]): WhatIfPayload {
  return whatIf(base, amounts.map((amount) => [`cash ${pyMoney(amount)}`, { cash_upfront: amount }]));
}

// ----- what the behave gateway and the UI call (support/gateway.py: EngineGateway) -------------------
export const simulateDict = (data: FlatInput): Payload => simulationToDict(simulate(inputFromDict(data)));
export const compareDicts = (rows: FlatInput[]): Summary[] => rows.map((r) => summaryToDict(simulate(inputFromDict(r))));
export const cashLadderDict = (data: FlatInput, amounts: number[]): WhatIfPayload => cashLadder(inputFromDict(data), amounts);
