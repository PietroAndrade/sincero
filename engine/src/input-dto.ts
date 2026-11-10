/**
 * The data: the three groups of values a simulation needs (ported from input_fields.py and
 * input_dto.py; the design is docs/simulation-input-split.md).
 *
 *     ContractData    what the buyer signs with the developer, and the amounts that follow from it alone
 *     MarketData      the economic environment: rates, financing term, fees, income ceiling
 *     BankCreditData  what the bank pre-approved and how a credit gap is paid
 *
 * Each DTO is frozen and has one responsibility. Only ContractData has behaviour, and only about
 * its own amounts. Validation rules live in validators.ts, orchestration in model.ts.
 *
 * FIELDS declares every field once: name, group, default. It is the source of truth now that the
 * .proto is retired (decision B of docs/decisions/engine-in-the-browser.md). Field names are unique
 * across the groups, so a flat `field -> value` mapping (a form, a JSON body, a what-if override)
 * is routed to its owner with FIELD_OWNER.
 */
import { InputShapeError } from "./errors.js";
import { maxOf } from "./numerics.js";

export type Group = "contract" | "market" | "bank_credit";

export interface FieldSpec {
  readonly name: string;
  readonly group: Group;
  /** Absent: the field is required. */
  readonly default?: number | string | null | readonly number[];
}

/** Every input field, in DTO order (Python's `field_names()`). */
export const FIELDS: readonly FieldSpec[] = Object.freeze([
  { name: "name", group: "contract" },
  { name: "list_price", group: "contract" },
  { name: "months_remaining", group: "contract" },
  { name: "down_payment_pct", group: "contract", default: 20.0 },
  { name: "fgts_upfront", group: "contract", default: 0.0 },
  { name: "cash_upfront", group: "contract", default: 0.0 },
  { name: "developer_installment", group: "contract", default: null },
  { name: "balloon_months", group: "contract", default: Object.freeze([]) },
  { name: "incc_rate_pa", group: "market", default: 7.0 },
  { name: "bank_rate_pa", group: "market", default: 10.26 },
  { name: "term_months", group: "market", default: 360 },
  { name: "itbi_pct", group: "market", default: 2.0 },
  { name: "registry_pct", group: "market", default: 0.5 },
  { name: "income_commitment_ratio", group: "market", default: 0.3 },
  { name: "pre_approved_credit", group: "bank_credit", default: null },
  { name: "pro_soluto_months", group: "bank_credit", default: 12 },
].map((f) => Object.freeze(f as FieldSpec)));

/** A flat `field -> value` mapping, as a form, a JSON body or a scenario builds it. */
export type FlatInput = Record<string, unknown>;

// ----- the fields of each group --------------------------------------------------------------------
/** The contract with the developer: the property, the down payment and how it is paid. */
export interface ContractFields {
  /** Label of the property. */
  readonly name: string;
  /** List price, R$. */
  readonly list_price: number;
  /** Months left until the building is delivered (time left, not the project's total duration). */
  readonly months_remaining: number;
  /** Down payment required by the developer, % of the list price. */
  readonly down_payment_pct: number;
  /** FGTS used at signing, R$. */
  readonly fgts_upfront: number;
  /** Cash paid at signing, R$; above the down payment it reduces the financed balance. */
  readonly cash_upfront: number;
  /**
   * Monthly amount paid to the developer during construction, R$. When null the remaining down
   * payment is split in equal installments; when the buyer chooses an amount, whatever it does not
   * cover is paid as balloons in `balloon_months` (the balloon amount is derived, never typed in).
   */
  readonly developer_installment: number | null;
  /** Construction months (1..months_remaining) with a balloon payment. */
  readonly balloon_months: readonly number[];
}

/** Market and regulatory conditions, independent of the property. */
export interface MarketFields {
  /** INCC, % per year. */
  readonly incc_rate_pa: number;
  /** Bank interest rate, % per year. */
  readonly bank_rate_pa: number;
  /** Bank financing term, months. */
  readonly term_months: number;
  /** ITBI, % of the list price. */
  readonly itbi_pct: number;
  /** Registry and deed costs, % of the list price. */
  readonly registry_pct: number;
  /** Max share of household income the bank accepts as installment, 0-1. */
  readonly income_commitment_ratio: number;
}

/** The bank's position at signing and the fallback when it falls short at delivery. */
export interface BankCreditFields {
  /** Credit pre-approved by the bank at signing, R$. When null: the nominal mortgage balance. */
  readonly pre_approved_credit: number | null;
  /** Months to pay the developer any credit gap (pro-soluto). */
  readonly pro_soluto_months: number;
}

type Required_ = "name" | "list_price" | "months_remaining";
/** What `new ContractData(…)` needs: the three required fields, any of the others. */
export type ContractInit = Pick<ContractFields, Required_> & Partial<Omit<ContractFields, Required_>>;

/**
 * Set `target`'s fields from `values`: each field of `group`, its default when absent (or
 * undefined), then freeze. An unknown or a missing required field is an InputShapeError.
 */
function assignFields(target: object, group: Group, values: object, owner: string): void {
  const specs = FIELDS.filter((f) => f.group === group);
  const given = values as Record<string, unknown>;
  const unknown = Object.keys(given).filter((k) => !specs.some((f) => f.name === k)).sort();
  if (unknown.length) throw new InputShapeError(`unknown ${owner} field(s): ${unknown.join(", ")}`, "unknown_fields", unknown);
  const missing: string[] = [];
  const out = target as Record<string, unknown>;
  for (const f of specs) {
    const value = given[f.name] !== undefined ? given[f.name] : f.default;
    if (value === undefined) missing.push(f.name);
    // a list is copied and frozen, as Python's __post_init__ turned it into a tuple
    else out[f.name] = Array.isArray(value) ? Object.freeze([...value]) : value;
  }
  if (missing.length)
    throw new InputShapeError(`missing required input field(s): ${missing.join(", ")}`, "missing_fields", missing);
  Object.freeze(target);
}

// ----- the DTOs ----------------------------------------------------------------------------------
/** The contract with the developer, plus the amounts that follow from it alone. */
export class ContractData implements ContractFields {
  static readonly group: Group = "contract";
  declare readonly name: string;
  declare readonly list_price: number;
  declare readonly months_remaining: number;
  declare readonly down_payment_pct: number;
  declare readonly fgts_upfront: number;
  declare readonly cash_upfront: number;
  declare readonly developer_installment: number | null;
  declare readonly balloon_months: readonly number[];

  constructor(fields: ContractInit) {
    assignFields(this, "contract", fields, "ContractData");
  }

  /** Down payment demanded by the developer: `list_price × down_payment_pct`. */
  get requiredDownPayment(): number {
    return (this.list_price * this.down_payment_pct) / 100.0;
  }

  /** Everything paid at signing (FGTS + cash). */
  get upfront(): number {
    return this.fgts_upfront + this.cash_upfront;
  }

  /** Down payment still owed to the developer after the upfront credits (never negative). */
  get remainingDownPayment(): number {
    return maxOf(0.0, this.requiredDownPayment - this.upfront);
  }
}

/** Market and regulatory conditions, independent of the property. */
export class MarketData implements MarketFields {
  static readonly group: Group = "market";
  declare readonly incc_rate_pa: number;
  declare readonly bank_rate_pa: number;
  declare readonly term_months: number;
  declare readonly itbi_pct: number;
  declare readonly registry_pct: number;
  declare readonly income_commitment_ratio: number;

  constructor(fields: Partial<MarketFields> = {}) {
    assignFields(this, "market", fields, "MarketData");
  }
}

/** The bank's position at signing and the fallback when it falls short at delivery. */
export class BankCreditData implements BankCreditFields {
  static readonly group: Group = "bank_credit";
  declare readonly pre_approved_credit: number | null;
  declare readonly pro_soluto_months: number;

  constructor(fields: Partial<BankCreditFields> = {}) {
    assignFields(this, "bank_credit", fields, "BankCreditData");
  }
}

export type InputDto = ContractData | MarketData | BankCreditData;

/** The DTO classes, in order. */
export const INPUT_GROUPS = Object.freeze([ContractData, MarketData, BankCreditData] as const);

/** Field name -> the DTO class that owns it. */
export const FIELD_OWNER: Readonly<Record<string, (typeof INPUT_GROUPS)[number]>> = Object.freeze(
  Object.fromEntries(FIELDS.map((f) => [f.name, INPUT_GROUPS.find((dto) => dto.group === f.group)!])),
);

/** Every input field, in DTO order. */
export const fieldNames = (): string[] => FIELDS.map((f) => f.name);

/** The default of every input field that has one. */
export const fieldDefaults = (): Record<string, FieldSpec["default"]> =>
  Object.fromEntries(FIELDS.filter((f) => f.default !== undefined).map((f) => [f.name, f.default]));

/** A copy of `dto` with some of its fields changed (Python's `dataclasses.replace`). */
export function replace(dto: ContractData, changes: Partial<ContractFields>): ContractData;
export function replace(dto: MarketData, changes: Partial<MarketFields>): MarketData;
export function replace(dto: BankCreditData, changes: Partial<BankCreditFields>): BankCreditData;
export function replace(dto: InputDto, changes: object): InputDto {
  const Dto = dto.constructor as new (fields: object) => InputDto;
  return new Dto({ ...dto, ...changes });
}
