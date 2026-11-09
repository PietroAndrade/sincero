/**
 * Port of app/models/: one section per Python module, same names, same order of floating-point
 * operations (so the figures agree to the bit, not just to the cent — see pyfloat.ts).
 */
import { pyMaxBy, pyMax, pyMoney, pySum } from "./pyfloat.js";
import {
  BankCreditData,
  ContractData,
  MarketData,
  SimulationError,
  SimulationInput,
  remainingDownPayment,
  requiredDownPayment,
  upfront,
} from "./inputs.js";
import { validate } from "./validators.js";

// ----- rates.py ----------------------------------------------------------------------------------
export const annualToMonthly = (ratePaPct: number): number => (1.0 + ratePaPct / 100.0) ** (1.0 / 12.0) - 1.0;

export class MonthlyRate {
  constructor(readonly annualPct: number) {}
  get monthly(): number {
    return annualToMonthly(this.annualPct);
  }
  factor(months: number): number {
    return (1.0 + this.monthly) ** months;
  }
}

// ----- down_payment.py ---------------------------------------------------------------------------
const CENT = 0.005;

export interface Balloon {
  month: number;
  nominal: number;
}

export interface DeveloperPayment {
  month: number;
  incc_factor: number;
  installment: number;
  balloon: number;
}

export class DownPaymentPlan {
  readonly required: number;
  readonly upfront: number;
  readonly remaining: number;
  readonly nominalInstallment: number;
  readonly balloons: Balloon[];
  readonly schedule: DeveloperPayment[];

  constructor(contract: ContractData, incc: MonthlyRate) {
    this.required = requiredDownPayment(contract);
    this.upfront = upfront(contract);
    this.remaining = remainingDownPayment(contract);
    const n = contract.months_remaining;
    [this.nominalInstallment, this.balloons] = this.sizePayments(contract, n);
    const balloonByMonth = new Map(this.balloons.map((b) => [b.month, b.nominal]));
    this.schedule = [];
    for (let k = 1; k <= n; k++) {
      this.schedule.push({
        month: k,
        incc_factor: incc.factor(k),
        installment: this.nominalInstallment * incc.factor(k),
        balloon: (balloonByMonth.get(k) ?? 0.0) * incc.factor(k),
      });
    }
  }

  private sizePayments(contract: ContractData, n: number): [number, Balloon[]] {
    if (contract.developer_installment === null) {
      if (contract.balloon_months.length)
        throw new SimulationError("a monthly developer installment is required to size the balloon payments");
      return [this.remaining / n, []];
    }
    const installment = contract.developer_installment;
    const covered = installment * n;
    const missing = this.remaining - covered;
    const rounding = CENT * n; // an installment rounded to the cent still "covers" the balance
    if (missing < -rounding)
      throw new SimulationError(
        `monthly installments of R$ ${pyMoney(covered)} exceed the down payment balance of R$ ${pyMoney(this.remaining)}`,
      );
    if (missing <= rounding) return [installment, []];
    if (!contract.balloon_months.length)
      throw new SimulationError(
        `monthly installments of R$ ${pyMoney(covered)} do not cover the down payment balance of ` +
          `R$ ${pyMoney(this.remaining)}; R$ ${pyMoney(missing)} is missing — add balloon months or raise the installment`,
      );
    const perBalloon = missing / contract.balloon_months.length;
    const months = [...contract.balloon_months].sort((a, b) => a - b);
    return [installment, months.map((month) => ({ month, nominal: perBalloon }))];
  }

  get missingAmount(): number {
    return pySum(this.balloons.map((b) => b.nominal));
  }
  get nominalBalloon(): number {
    return this.balloons.length ? this.balloons[0].nominal : 0.0;
  }
  get totalPaid(): number {
    return pySum(this.schedule.map((p) => p.installment + p.balloon));
  }
  get inccCorrection(): number {
    return this.totalPaid - this.remaining;
  }
}

// ----- mortgage.py -------------------------------------------------------------------------------
export class MortgageBalance {
  readonly months: number;
  readonly nominal: number;

  constructor(contract: ContractData, private readonly incc: MonthlyRate) {
    this.months = contract.months_remaining;
    // Upfront above the required down payment reduces what is financed.
    this.nominal = contract.list_price - pyMax(requiredDownPayment(contract), upfront(contract));
  }
  atMonth(month: number): number {
    return this.nominal * this.incc.factor(month);
  }
  get corrected(): number {
    return this.atMonth(this.months);
  }
  get hiddenInccDebt(): number {
    return this.corrected - this.nominal;
  }
}

// ----- construction.py ---------------------------------------------------------------------------
export interface ConstructionCharge {
  month: number;
  released_share: number;
  released_balance: number;
  interest: number;
}

export class ConstructionInterest {
  readonly schedule: ConstructionCharge[] = [];

  constructor(mortgage: MortgageBalance, bank: MonthlyRate) {
    const months = mortgage.months; // LinearRelease: k/N released after month k
    for (let k = 1; k <= months; k++) {
      const share = k / months;
      const released = mortgage.atMonth(k) * share;
      this.schedule.push({ month: k, released_share: share, released_balance: released, interest: released * bank.monthly });
    }
  }
  get total(): number {
    return pySum(this.schedule.map((c) => c.interest));
  }
}

// ----- closing_costs.py --------------------------------------------------------------------------
export class ClosingCosts {
  readonly itbi: number;
  readonly registry: number;
  constructor(listPrice: number, market: MarketData) {
    this.itbi = (listPrice * market.itbi_pct) / 100.0;
    this.registry = (listPrice * market.registry_pct) / 100.0;
  }
  get total(): number {
    return this.itbi + this.registry;
  }
}

// ----- amortization.py ---------------------------------------------------------------------------
export interface Installment {
  month: number;
  installment: number;
  interest: number;
  amortization: number;
  outstanding: number;
}

export abstract class AmortizationSchedule {
  readonly schedule: Installment[];
  constructor(
    readonly principal: number,
    readonly rate: MonthlyRate,
    readonly termMonths: number,
    readonly incomeRatio: number,
  ) {
    this.schedule = this.build();
  }
  protected abstract build(): Installment[];
  get firstInstallment(): number {
    return this.schedule[0].installment;
  }
  get lastInstallment(): number {
    return this.schedule[this.schedule.length - 1].installment;
  }
  get totalInterest(): number {
    return pySum(this.schedule.map((i) => i.interest));
  }
  get totalPaid(): number {
    return pySum(this.schedule.map((i) => i.installment));
  }
  get minIncome(): number {
    return this.firstInstallment / this.incomeRatio;
  }
}

export class SacSchedule extends AmortizationSchedule {
  get amortization(): number {
    return this.principal / this.termMonths;
  }
  protected build(): Installment[] {
    const amort = this.principal / this.termMonths;
    const i = this.rate.monthly;
    const rows: Installment[] = [];
    let outstanding = this.principal;
    for (let k = 1; k <= this.termMonths; k++) {
      const interest = outstanding * i;
      outstanding -= amort;
      rows.push({ month: k, installment: amort + interest, interest, amortization: amort, outstanding });
    }
    return rows;
  }
}

export class PriceSchedule extends AmortizationSchedule {
  get installment(): number {
    const i = this.rate.monthly;
    if (i === 0) return this.principal / this.termMonths;
    return (this.principal * i) / (1 - (1 + i) ** -this.termMonths);
  }
  protected build(): Installment[] {
    const pmt = this.installment;
    const i = this.rate.monthly;
    const rows: Installment[] = [];
    let outstanding = this.principal;
    for (let k = 1; k <= this.termMonths; k++) {
      const interest = outstanding * i;
      const amort = pmt - interest;
      outstanding -= amort;
      rows.push({ month: k, installment: pmt, interest, amortization: amort, outstanding });
    }
    return rows;
  }
}

// ----- credit_gap.py -----------------------------------------------------------------------------
export class CreditGap {
  readonly preApproved: number;
  readonly needed: number;
  readonly gap: number;
  readonly proSolutoMonths: number;
  readonly proSolutoInstallment: number;
  constructor(credit: BankCreditData, mortgage: MortgageBalance) {
    this.preApproved = credit.pre_approved_credit !== null ? credit.pre_approved_credit : mortgage.nominal;
    this.needed = mortgage.corrected;
    this.gap = pyMax(0.0, this.needed - this.preApproved);
    this.proSolutoMonths = credit.pro_soluto_months;
    this.proSolutoInstallment = credit.pro_soluto_months > 0 ? this.gap / credit.pro_soluto_months : 0.0;
  }
}

// ----- total_cost.py -----------------------------------------------------------------------------
export interface CostLine {
  component: string;
  base_value: number;
  additional: number;
}

export class TotalCost {
  readonly lines: CostLine[];
  constructor(
    readonly listPrice: number,
    dp: DownPaymentPlan,
    mortgage: MortgageBalance,
    construction: ConstructionInterest,
    closing: ClosingCosts,
  ) {
    this.lines = [
      // the base column adds up to the list price even when upfront > down payment
      { component: "Down payment", base_value: pyMax(dp.required, dp.upfront), additional: dp.inccCorrection },
      { component: "Mortgage balance", base_value: mortgage.nominal, additional: mortgage.hiddenInccDebt },
      { component: "Construction interest", base_value: 0.0, additional: construction.total },
      { component: "Closing costs", base_value: 0.0, additional: closing.total },
    ];
  }
  get additional(): number {
    return pySum(this.lines.map((l) => l.additional));
  }
  get total(): number {
    return this.listPrice + this.additional;
  }
  get extraPct(): number {
    return (this.additional / this.listPrice) * 100.0;
  }
  get totalLine(): CostLine {
    return { component: "Total", base_value: this.listPrice, additional: this.additional };
  }
}

// ----- timeline.py -------------------------------------------------------------------------------
export interface TimelineMonth {
  month: number;
  developer_installment: number;
  balloon: number;
  construction_interest: number;
  bank_installment: number;
  upfront: number;
}

export const monthTotal = (m: TimelineMonth): number =>
  m.developer_installment + m.balloon + m.construction_interest + m.bank_installment + m.upfront;

const timelineMonth = (month: number, values: Partial<TimelineMonth> = {}): TimelineMonth => ({
  month,
  developer_installment: 0.0,
  balloon: 0.0,
  construction_interest: 0.0,
  bank_installment: 0.0,
  upfront: 0.0,
  ...values,
});

export class CashFlowTimeline {
  readonly months: TimelineMonth[];
  readonly constructionPhase: TimelineMonth[];
  readonly peak: TimelineMonth;

  constructor(dp: DownPaymentPlan, construction: ConstructionInterest, bank: AmortizationSchedule) {
    const n = dp.schedule.length;
    this.months = [timelineMonth(0, { upfront: dp.upfront })];
    const pairs = Math.min(dp.schedule.length, construction.schedule.length); // zip()
    for (let j = 0; j < pairs; j++) {
      const d = dp.schedule[j];
      const c = construction.schedule[j];
      this.months.push(
        timelineMonth(d.month, { developer_installment: d.installment, balloon: d.balloon, construction_interest: c.interest }),
      );
    }
    for (const i of bank.schedule) this.months.push(timelineMonth(n + i.month, { bank_installment: i.installment }));
    this.constructionPhase = this.months.slice(0, n + 1);
    this.peak = pyMaxBy(this.constructionPhase, monthTotal);
  }
  get constructionPhaseTotal(): number {
    return pySum(this.constructionPhase.map(monthTotal));
  }
}

// ----- simulator.py ------------------------------------------------------------------------------
export interface SimulationResult {
  input: SimulationInput;
  incc: MonthlyRate;
  bank: MonthlyRate;
  downPayment: DownPaymentPlan;
  mortgage: MortgageBalance;
  constructionInterest: ConstructionInterest;
  closingCosts: ClosingCosts;
  sac: SacSchedule;
  price: PriceSchedule;
  creditGap: CreditGap;
  totalCost: TotalCost;
  timeline: CashFlowTimeline;
}

export function simulate(raw: SimulationInput): SimulationResult {
  const input = validate(raw);
  const { contract, market, bank_credit: credit } = input;
  const incc = new MonthlyRate(market.incc_rate_pa);
  const bank = new MonthlyRate(market.bank_rate_pa);

  const downPayment = new DownPaymentPlan(contract, incc);
  const mortgage = new MortgageBalance(contract, incc);
  const constructionInterest = new ConstructionInterest(mortgage, bank);
  const closingCosts = new ClosingCosts(contract.list_price, market);
  const sac = new SacSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio);
  const price = new PriceSchedule(mortgage.corrected, bank, market.term_months, market.income_commitment_ratio);
  const creditGap = new CreditGap(credit, mortgage);
  const totalCost = new TotalCost(contract.list_price, downPayment, mortgage, constructionInterest, closingCosts);
  const timeline = new CashFlowTimeline(downPayment, constructionInterest, sac);

  return { input, incc, bank, downPayment, mortgage, constructionInterest, closingCosts, sac, price, creditGap, totalCost, timeline };
}
