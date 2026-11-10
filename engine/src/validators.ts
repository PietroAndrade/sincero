/**
 * Input validation rules, one small validator per concern (validators.py).
 *
 * A validator receives only the DTO it judges (`Validator<ContractData>`, `Validator<MarketData>` or
 * `Validator<BankCreditData>`) and throws `SimulationError` with a message for the buyer on the first
 * rule it finds broken, with a code, the fields to blame and the params of the message (errors.ts).
 * The messages are the ones the scenarios pin, verbatim.
 * `CompositeValidator` chains validators of the same DTO in a fixed order, so the error a buyer sees
 * is always the most fundamental one.
 *
 * `ValidationPolicy` bundles one validator per DTO; `DEFAULT_POLICY` is the application's.
 * `SimulationInput.validate()` applies a policy to its three DTOs. Components that need a different
 * policy (a test, later perhaps the UI) build their own. A new rule is a new validator appended to
 * the policy.
 */
import { reject } from "./errors.js";
import type { BankCreditData, ContractData, MarketData } from "./input-dto.js";
import { formatAmount } from "./numerics.js";

/** One validation concern over one DTO. Throws `SimulationError` on the first broken rule. */
export abstract class Validator<T> {
  constructor() {
    if (new.target === Validator) throw new TypeError("Validator is abstract: extend it");
  }
  abstract validate(data: T): void;
}

// ----- contract with the developer ---------------------------------------------------------------
/** The property itself: price, time left until delivery, required down payment. */
export class PropertyValidator extends Validator<ContractData> {
  validate(c: ContractData): void {
    if (c.list_price <= 0) throw reject("list_price_not_positive", { list_price: c.list_price }, ["list_price"]);
    if (c.months_remaining < 1)
      throw reject("months_remaining_below_one", { months_remaining: c.months_remaining }, ["months_remaining"]);
    if (!(0 <= c.down_payment_pct && c.down_payment_pct <= 100))
      throw reject("down_payment_pct_out_of_range", { down_payment_pct: c.down_payment_pct }, ["down_payment_pct"]);
  }
}

/**
 * What the buyer brings at signing. FGTS and cash may together cover the whole price (a cash
 * purchase: nothing left to finance) but never more: there is nothing to pay the excess for, and
 * the model would otherwise finance a negative balance.
 */
export class UpfrontPaymentsValidator extends Validator<ContractData> {
  validate(c: ContractData): void {
    if (c.fgts_upfront < 0 || c.cash_upfront < 0)
      throw reject(
        "upfront_negative",
        { fgts_upfront: c.fgts_upfront, cash_upfront: c.cash_upfront },
        (["fgts_upfront", "cash_upfront"] as const).filter((f) => c[f] < 0),
      );
    if (c.upfront > c.list_price)
      throw reject("upfront_above_list_price", { upfront: c.upfront, list_price: c.list_price }, ["fgts_upfront", "cash_upfront"]);
  }
}

/**
 * The payment plan agreed with the developer: monthly installment and balloon months. Whether the
 * installments and balloons actually cover the balance is a sizing question answered by
 * `DownPaymentPlan`, not a shape question answered here.
 */
export class DeveloperPlanValidator extends Validator<ContractData> {
  validate(c: ContractData): void {
    if (c.developer_installment !== null && c.developer_installment < 0)
      throw reject("developer_installment_negative", { developer_installment: c.developer_installment }, ["developer_installment"]);
    for (const month of c.balloon_months) {
      if (month > c.months_remaining)
        throw reject(
          "balloon_month_after_delivery",
          { month, months_remaining: c.months_remaining },
          ["balloon_months", "months_remaining"],
        );
      if (month < 1) throw reject("balloon_month_below_one", { month }, ["balloon_months"]);
    }
    const repeated = c.balloon_months.find((month, i) => c.balloon_months.indexOf(month) !== i);
    if (repeated !== undefined) throw reject("balloon_months_repeated", { month: repeated }, ["balloon_months"]);
  }
}

// ----- market ------------------------------------------------------------------------------------
/**
 * Annual rates that are compounded monthly. INCC may be negative (deflation) but an annual rate of
 * -100% or below has no monthly equivalent; a bank never lends at a negative rate.
 */
export class MarketRatesValidator extends Validator<MarketData> {
  validate(m: MarketData): void {
    if (m.incc_rate_pa <= -100) throw reject("incc_rate_too_low", { incc_rate_pa: m.incc_rate_pa }, ["incc_rate_pa"]);
    if (m.bank_rate_pa < 0) throw reject("bank_rate_negative", { bank_rate_pa: m.bank_rate_pa }, ["bank_rate_pa"]);
  }
}

/** Terms of the bank financing after key handover. */
export class FinancingValidator extends Validator<MarketData> {
  validate(m: MarketData): void {
    if (m.term_months < 1) throw reject("term_months_below_one", { term_months: m.term_months }, ["term_months"]);
    if (!(0 < m.income_commitment_ratio && m.income_commitment_ratio <= 1))
      throw reject(
        "income_commitment_ratio_out_of_range",
        { income_commitment_ratio: m.income_commitment_ratio },
        ["income_commitment_ratio"],
      );
  }
}

/** ITBI and registry/deed, as percentages of the list price. */
export class ClosingCostsValidator extends Validator<MarketData> {
  validate(m: MarketData): void {
    if (m.itbi_pct < 0 || m.registry_pct < 0)
      throw reject(
        "closing_cost_pct_negative",
        { itbi_pct: m.itbi_pct, registry_pct: m.registry_pct },
        (["itbi_pct", "registry_pct"] as const).filter((f) => m[f] < 0),
      );
  }
}

// ----- bank credit -------------------------------------------------------------------------------
/** Pre-approved credit and the pro-soluto term used to pay any credit gap. */
export class BankCreditValidator extends Validator<BankCreditData> {
  validate(b: BankCreditData): void {
    if (b.pre_approved_credit !== null && b.pre_approved_credit < 0)
      throw reject("pre_approved_credit_negative", { pre_approved_credit: b.pre_approved_credit }, ["pre_approved_credit"]);
    if (b.pro_soluto_months < 1)
      throw reject("pro_soluto_months_below_one", { pro_soluto_months: b.pro_soluto_months }, ["pro_soluto_months"]);
  }
}

// ----- a cash ladder ------------------------------------------------------------------------------
/** What the cash-ladder rules judge: the amounts, and the list price they are measured against. */
export interface CashLadderAmounts {
  readonly amounts: readonly number[];
  readonly list_price: number;
}

/**
 * The amounts of a cash ladder (backlog US-07 AC4-AC5): each a finite number, not negative, not
 * above the list price, and each greater than the one before. The first offending amount is named,
 * in order, and no row is computed. "Greater" is to the cent: two amounts with the same cents would
 * be one row (rows are labelled `cash 30,000.00`), so the second is refused rather than dropped.
 *
 * FGTS + an amount above the list price is the model's rule (`upfront_above_list_price`), reported
 * when that rung is simulated; this rule is about the amount alone.
 */
export class CashLadderValidator extends Validator<CashLadderAmounts> {
  validate({ amounts, list_price }: CashLadderAmounts): void {
    amounts.forEach((amount, index) => {
      const fields = [`amounts[${index}]`];
      if (typeof amount !== "number" || !Number.isFinite(amount)) throw reject("cash_ladder_amount_not_finite", { index }, fields);
      if (amount < 0) throw reject("cash_ladder_amount_negative", { index, amount }, fields);
      if (amount > list_price) throw reject("cash_ladder_amount_above_list_price", { index, amount, list_price }, fields);
      const previous = amounts[index - 1];
      if (previous !== undefined && (amount <= previous || formatAmount(amount) === formatAmount(previous)))
        throw reject("cash_ladder_amounts_not_increasing", { index, amount, previous }, fields);
    });
  }
}

// ----- composition -------------------------------------------------------------------------------
/** Runs validators of the same DTO in order; the first `SimulationError` thrown wins. */
export class CompositeValidator<T> extends Validator<T> {
  readonly validators: readonly Validator<T>[];

  constructor(validators: Iterable<Validator<T>>) {
    super();
    this.validators = Object.freeze([...validators]);
  }

  validate(data: T): void {
    for (const validator of this.validators) validator.validate(data);
  }
}

/**
 * One validator per DTO. `SimulationInput.validate()` applies them contract -> market -> bank
 * credit. The type parameters keep what a policy is built with (DEFAULT_POLICY's validators are
 * composites, and say so); anywhere a policy is expected, any validators will do.
 */
export class ValidationPolicy<
  C extends Validator<ContractData> = Validator<ContractData>,
  M extends Validator<MarketData> = Validator<MarketData>,
  B extends Validator<BankCreditData> = Validator<BankCreditData>,
> {
  constructor(
    readonly contract: C,
    readonly market: M,
    readonly bank_credit: B,
  ) {
    Object.freeze(this);
  }
}

export const DEFAULT_POLICY = new ValidationPolicy(
  new CompositeValidator<ContractData>([new PropertyValidator(), new UpfrontPaymentsValidator(), new DeveloperPlanValidator()]),
  new CompositeValidator<MarketData>([new MarketRatesValidator(), new FinancingValidator(), new ClosingCostsValidator()]),
  new CompositeValidator<BankCreditData>([new BankCreditValidator()]),
);
