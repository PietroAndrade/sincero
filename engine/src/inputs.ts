/**
 * The composition (inputs.py): a simulation input is a ContractData, a MarketData and a
 * BankCreditData, validated together and varied together. Components read the DTO they need
 * (`DownPaymentPlan(input.contract, …)`), never the whole input.
 *
 * Flat outside, grouped inside: forms, JSON bodies and what-if overrides are flat `field -> value`
 * mappings. `fromDict` routes each field to the DTO that owns it, and `toDict` flattens back.
 */
import { InputShapeError } from "./errors.js";
import { BankCreditData, ContractData, FIELD_OWNER, FIELDS, MarketData, replace } from "./input-dto.js";
import type { BankCreditFields, ContractFields, ContractInit, FlatInput, Group, MarketFields } from "./input-dto.js";
import type { SimulationInputInterface } from "./input-interface.js";
import { DEFAULT_POLICY } from "./validators.js";
import type { ValidationPolicy } from "./validators.js";

export class SimulationInput implements SimulationInputInterface {
  constructor(
    readonly contract: ContractData,
    readonly market: MarketData = new MarketData(),
    readonly bank_credit: BankCreditData = new BankCreditData(),
  ) {
    Object.freeze(this);
  }

  /** Apply `policy` to each DTO (contract -> market -> bank credit) and return this input. */
  validate(policy: ValidationPolicy = DEFAULT_POLICY): this {
    policy.contract.validate(this.contract);
    policy.market.validate(this.market);
    policy.bank_credit.validate(this.bank_credit);
    return this;
  }

  /** A copy with some fields changed, across DTO boundaries. An unknown field is an InputShapeError. */
  withOverrides(overrides: FlatInput): SimulationInput {
    const grouped = group(overrides);
    return new SimulationInput(
      replace(this.contract, grouped.contract as Partial<ContractFields>),
      replace(this.market, grouped.market as Partial<MarketFields>),
      replace(this.bank_credit, grouped.bank_credit as Partial<BankCreditFields>),
    );
  }

  /** Build an input from the flat form, each field to the DTO that owns it. */
  static fromDict(data: FlatInput): SimulationInput {
    const grouped = group(data);
    return new SimulationInput(
      new ContractData(grouped.contract as ContractInit),
      new MarketData(grouped.market as Partial<MarketFields>),
      new BankCreditData(grouped.bank_credit as Partial<BankCreditFields>),
    );
  }

  /** The flat `field -> value` form, every field in FIELDS order; the inverse of `fromDict`. */
  toDict(): FlatInput {
    const out: FlatInput = {};
    for (const f of FIELDS) {
      const value = (this[f.group] as unknown as Record<string, unknown>)[f.name];
      out[f.name] = Array.isArray(value) ? [...value] : value;
    }
    return out;
  }
}

/** Split a flat mapping by owning DTO; an unknown field is an InputShapeError. */
function group(data: FlatInput): Record<Group, Record<string, unknown>> {
  const unknown = Object.keys(data).filter((k) => !Object.hasOwn(FIELD_OWNER, k)).sort();
  if (unknown.length)
    throw new InputShapeError(`unknown simulation input field(s): ${unknown.join(", ")}`, "unknown_fields", unknown);
  const grouped: Record<Group, Record<string, unknown>> = { contract: {}, market: {}, bank_credit: {} };
  for (const [name, value] of Object.entries(data)) grouped[FIELD_OWNER[name]!.group][name] = value;
  return grouped;
}
