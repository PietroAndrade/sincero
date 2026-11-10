/**
 * The engine's two errors, structured (plan item P1.5): besides the English message, each carries
 *
 *   code     what went wrong, one code per cause (`upfront_above_list_price`): the key a UI translates
 *   fields   the input fields involved, to mark on a form (`["fgts_upfront", "cash_upfront"]`), or
 *            `amounts[i]` for an amount of a cash ladder; empty when no field is to blame
 *   params   the numbers the message is made of, raw (`{ upfront: 513000, list_price: 440000 }`)
 *
 * The English message is BUILT from the code and the params, by MESSAGES below, so a translation
 * needs nothing else and never parses prose. The messages are the ones the scenarios pin, verbatim;
 * the golden master checks every one of them.
 */
import { formatAmount } from "./numerics.js";

const R$ = (x: number): string => `R$ ${formatAmount(x)}`;

/** The params of each code of a SimulationError (a business rule). */
export interface SimulationErrorParams {
  // the property (PropertyValidator)
  list_price_not_positive: { list_price: number };
  months_remaining_below_one: { months_remaining: number };
  down_payment_pct_out_of_range: { down_payment_pct: number };
  // what the buyer brings at signing (UpfrontPaymentsValidator)
  upfront_negative: { fgts_upfront: number; cash_upfront: number };
  upfront_above_list_price: { upfront: number; list_price: number };
  // the developer plan (DeveloperPlanValidator)
  developer_installment_negative: { developer_installment: number };
  balloon_month_after_delivery: { month: number; months_remaining: number };
  balloon_month_below_one: { month: number };
  balloon_months_repeated: { month: number };
  // sizing the developer plan (DownPaymentPlan)
  balloons_without_installment: Record<string, never>;
  installments_exceed_balance: { covered: number; remaining: number };
  installments_leave_balance: { covered: number; remaining: number; missing: number };
  // the market (MarketRatesValidator, FinancingValidator, ClosingCostsValidator)
  incc_rate_too_low: { incc_rate_pa: number };
  bank_rate_negative: { bank_rate_pa: number };
  term_months_below_one: { term_months: number };
  income_commitment_ratio_out_of_range: { income_commitment_ratio: number };
  closing_cost_pct_negative: { itbi_pct: number; registry_pct: number };
  // the bank credit (BankCreditValidator)
  pre_approved_credit_negative: { pre_approved_credit: number };
  pro_soluto_months_below_one: { pro_soluto_months: number };
  // the amounts of a cash ladder (CashLadderValidator); index: the amount's position, from 0
  cash_ladder_amount_not_finite: { index: number };
  cash_ladder_amount_negative: { index: number; amount: number };
  cash_ladder_amount_above_list_price: { index: number; amount: number; list_price: number };
  cash_ladder_amounts_not_increasing: { index: number; amount: number; previous: number };
}

export type SimulationErrorCode = keyof SimulationErrorParams;

/** The English message of each code, from its params: the text the scenarios pin. */
export const MESSAGES: { readonly [C in SimulationErrorCode]: (p: SimulationErrorParams[C]) => string } = Object.freeze({
  list_price_not_positive: () => "list price must be greater than zero",
  months_remaining_below_one: () => "months remaining until delivery must be at least 1",
  down_payment_pct_out_of_range: () => "down payment percentage must be between 0 and 100",
  upfront_negative: () => "upfront payments must not be negative",
  upfront_above_list_price: (p) => `upfront payments of ${R$(p.upfront)} exceed the list price of ${R$(p.list_price)}`,
  developer_installment_negative: () => "the monthly developer installment must not be negative",
  balloon_month_after_delivery: (p) => `balloon month ${p.month} is after delivery (month ${p.months_remaining})`,
  balloon_month_below_one: (p) => `balloon month ${p.month} must be at least 1`,
  balloon_months_repeated: () => "balloon months must not repeat",
  balloons_without_installment: () => "a monthly developer installment is required to size the balloon payments",
  installments_exceed_balance: (p) =>
    `monthly installments of ${R$(p.covered)} exceed the down payment balance of ${R$(p.remaining)}`,
  installments_leave_balance: (p) =>
    `monthly installments of ${R$(p.covered)} do not cover the down payment balance of ${R$(p.remaining)}; ` +
    `${R$(p.missing)} is missing — add balloon months or raise the installment`,
  incc_rate_too_low: () => "INCC rate must be greater than -100% per year",
  bank_rate_negative: () => "bank interest rate must not be negative",
  term_months_below_one: () => "financing term must be at least 1 month",
  income_commitment_ratio_out_of_range: () => "income commitment ratio must be between 0 and 1",
  closing_cost_pct_negative: () => "closing cost percentages must not be negative",
  pre_approved_credit_negative: () => "pre-approved credit must not be negative",
  pro_soluto_months_below_one: () => "pro-soluto term must be at least 1 month",
  cash_ladder_amount_not_finite: (p) => `cash ladder amount #${p.index + 1} is not a finite number`,
  cash_ladder_amount_negative: (p) => `cash ladder amount ${R$(p.amount)} must not be negative`,
  cash_ladder_amount_above_list_price: (p) => `cash ladder amount ${R$(p.amount)} exceeds the list price of ${R$(p.list_price)}`,
  cash_ladder_amounts_not_increasing: (p) =>
    `cash ladder amounts must increase: ${R$(p.amount)} comes after ${R$(p.previous)}`,
});

export interface ErrorDetails {
  readonly code: string;
  readonly fields?: readonly string[];
  readonly params?: Readonly<Record<string, number>>;
}

/** A business rule rejects the input. */
export class SimulationError extends Error {
  override name = "SimulationError";
  /** One of SimulationErrorCode for the engine's own rules; a custom validator may use its own. */
  readonly code: string;
  readonly fields: readonly string[];
  readonly params: Readonly<Record<string, number>>;

  constructor(message: string, details: ErrorDetails = { code: "rejected" }) {
    super(message);
    this.code = details.code;
    this.fields = Object.freeze([...(details.fields ?? [])]);
    this.params = Object.freeze({ ...details.params });
  }
}

/** The engine's way to reject: the message is built from the code and the params. */
export function reject<C extends SimulationErrorCode>(
  code: C,
  params: SimulationErrorParams[C],
  fields: readonly string[],
): SimulationError {
  return new SimulationError(MESSAGES[code](params), { code, fields, params: params as Record<string, number> });
}

/** The codes of an InputShapeError. */
export type InputShapeErrorCode = "unknown_fields" | "missing_fields" | "balloon_months_not_a_list";

/**
 * The input is not a simulation input at all: an unknown or a missing field. Not a business rule
 * (the retired Python engine raised `TypeError` here), so its text is not part of the
 * specification; `fields` names the fields (a required field left empty on a form is
 * `missing_fields`).
 */
export class InputShapeError extends Error {
  override name = "InputShapeError";
  readonly code: InputShapeErrorCode;
  readonly fields: readonly string[];

  constructor(message: string, code: InputShapeErrorCode, fields: readonly string[]) {
    super(message);
    this.code = code;
    this.fields = Object.freeze([...fields]);
  }
}
