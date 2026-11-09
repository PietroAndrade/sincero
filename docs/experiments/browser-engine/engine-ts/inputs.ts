/**
 * Port of app/models/input_fields.py + input_dto.py + inputs.py (+ json_view.input_from_dict):
 * the three input groups, their defaults, and the flat `field -> value` form.
 *
 * The field table is written by hand here. harness/check_fields.py compares it with the Python
 * DTOs (which are generated from proto/sincero/simulation_input.proto), so a drift fails loudly;
 * a production port would generate it from the .proto, as `make dto` does for Python.
 */
import { pyMax } from "./pyfloat.js";

export class SimulationError extends Error {
  override name = "SimulationError";
}

/** Python raises `TypeError` for these (unknown field, missing required field): not a model rule. */
export class InputShapeError extends Error {
  override name = "InputShapeError";
}

export type Group = "contract" | "market" | "bank_credit";

export interface FieldSpec {
  name: string;
  group: Group;
  /** undefined: required (no default). */
  default?: number | string | null | readonly number[];
}

// In SimulationInput order (= Python `field_names()`).
export const FIELDS: readonly FieldSpec[] = [
  { name: "name", group: "contract" },
  { name: "list_price", group: "contract" },
  { name: "months_remaining", group: "contract" },
  { name: "down_payment_pct", group: "contract", default: 20.0 },
  { name: "fgts_upfront", group: "contract", default: 0.0 },
  { name: "cash_upfront", group: "contract", default: 0.0 },
  { name: "developer_installment", group: "contract", default: null },
  { name: "balloon_months", group: "contract", default: [] },
  { name: "incc_rate_pa", group: "market", default: 7.0 },
  { name: "bank_rate_pa", group: "market", default: 10.26 },
  { name: "term_months", group: "market", default: 360 },
  { name: "itbi_pct", group: "market", default: 2.0 },
  { name: "registry_pct", group: "market", default: 0.5 },
  { name: "income_commitment_ratio", group: "market", default: 0.3 },
  { name: "pre_approved_credit", group: "bank_credit", default: null },
  { name: "pro_soluto_months", group: "bank_credit", default: 12 },
];

export interface ContractData {
  readonly name: string;
  readonly list_price: number;
  readonly months_remaining: number;
  readonly down_payment_pct: number;
  readonly fgts_upfront: number;
  readonly cash_upfront: number;
  readonly developer_installment: number | null;
  readonly balloon_months: readonly number[];
}

export interface MarketData {
  readonly incc_rate_pa: number;
  readonly bank_rate_pa: number;
  readonly term_months: number;
  readonly itbi_pct: number;
  readonly registry_pct: number;
  readonly income_commitment_ratio: number;
}

export interface BankCreditData {
  readonly pre_approved_credit: number | null;
  readonly pro_soluto_months: number;
}

export interface SimulationInput {
  readonly contract: ContractData;
  readonly market: MarketData;
  readonly bank_credit: BankCreditData;
}

/** A flat mapping, as a JSON body or a behave world builds it. */
export type FlatInput = Record<string, unknown>;

// ----- the amounts a ContractData derives from its own fields (input_dto.ContractData) -----------
export const requiredDownPayment = (c: ContractData): number => (c.list_price * c.down_payment_pct) / 100.0;
export const upfront = (c: ContractData): number => c.fgts_upfront + c.cash_upfront;
export const remainingDownPayment = (c: ContractData): number => pyMax(0.0, requiredDownPayment(c) - upfront(c));

/** `input_from_dict` + `SimulationInput.from_dict`: route each field to its group, apply defaults. */
export function inputFromDict(data: FlatInput): SimulationInput {
  const known = new Set(FIELDS.map((f) => f.name));
  const unknown = Object.keys(data).filter((k) => !known.has(k)).sort();
  if (unknown.length) throw new InputShapeError(`unknown simulation input field(s): ${unknown.join(", ")}`);

  const groups: Record<Group, Record<string, unknown>> = { contract: {}, market: {}, bank_credit: {} };
  const missing: string[] = [];
  for (const f of FIELDS) {
    if (f.name in data) groups[f.group][f.name] = data[f.name];
    else if (f.default === undefined) missing.push(f.name);
    else groups[f.group][f.name] = Array.isArray(f.default) ? [...f.default] : f.default;
  }
  if (missing.length) throw new InputShapeError(`missing required input field(s): ${missing.join(", ")}`);
  // input_from_dict: `tuple(int(m) for m in balloon_months)`
  groups.contract.balloon_months = ((groups.contract.balloon_months as unknown[]) ?? []).map((m) => Math.trunc(Number(m)));
  return {
    contract: Object.freeze(groups.contract) as unknown as ContractData,
    market: Object.freeze(groups.market) as unknown as MarketData,
    bank_credit: Object.freeze(groups.bank_credit) as unknown as BankCreditData,
  };
}

/** `SimulationInput.with_overrides(**overrides)`: a copy with some fields changed. */
export function withOverrides(inp: SimulationInput, overrides: FlatInput): SimulationInput {
  return inputFromDict({ ...inputToDict(inp), ...overrides });
}

/** `json_view.input_to_dict`: the flat form, every field, in field order. */
export function inputToDict(inp: SimulationInput): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of FIELDS) {
    const value = (inp[f.group] as unknown as Record<string, unknown>)[f.name];
    out[f.name] = Array.isArray(value) ? [...value] : value;
  }
  return out;
}
