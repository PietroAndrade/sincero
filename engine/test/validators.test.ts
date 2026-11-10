/**
 * The input DTOs, the behavioural interface, the composed SimulationInput and the small validators.
 *
 * Ported from the retired tests/test_validators.py (19 tests): the same cases and assertions. Where
 * an assertion was about Python itself, it is replaced by its TypeScript equivalent:
 *
 *   frozen dataclass (FrozenInstanceError)   Object.isFrozen, and assigning throws TypeError
 *   dataclasses.fields(dto)                  the instance's own keys (the fields, in FIELDS order)
 *   "public members" (vars(cls))             the prototype's own names: getters and methods
 *   an ABC that cannot be instantiated       `abstract` (a compile error) and a TypeError at run time
 *   a pure ABC: no attributes, only          an interface: erased at run time, so it cannot hold
 *   abstract methods                         data or code; its keys are checked by the type checker
 *   ==, hash                                 toStrictEqual (same class, same fields), same flat form
 *   TypeError (unknown or missing field)     InputShapeError
 *   "a validator sees only its DTO"          a compile error when it is given anything else
 *
 * The type assertions (expectTypeOf, @ts-expect-error) run in `npm run typecheck`, part of `npm test`.
 */
import { describe, expect, expectTypeOf, it } from "vitest";
import {
  BankCreditData,
  CompositeValidator,
  ContractData,
  DEFAULT_POLICY,
  InputShapeError,
  MarketData,
  SimulationError,
  SimulationInput,
  ValidationPolicy,
  Validator,
  fieldDefaults,
  fieldNames,
} from "../src/index.js";
import type { FlatInput, SimulationInputInterface } from "../src/index.js";
import { FIELD_OWNER, INPUT_GROUPS, replace } from "../src/input-dto.js";
import {
  BankCreditValidator,
  ClosingCostsValidator,
  DeveloperPlanValidator,
  FinancingValidator,
  MarketRatesValidator,
  PropertyValidator,
  UpfrontPaymentsValidator,
} from "../src/validators.js";
import { expectApprox } from "./approx.js";
import { B, C, M, ra } from "./fixtures.js";

const ownNames = (cls: { prototype: object }) => Object.getOwnPropertyNames(cls.prototype).filter((n) => n !== "constructor");

// ----- the DTOs ----------------------------------------------------------------------------------
describe("the DTOs", () => {
  it("are frozen", () => {
    for (const dto of [C, M, B]) expect(Object.isFrozen(dto)).toBe(true);
    expect(() => {
      // @ts-expect-error: the fields are readonly
      new MarketData().incc_rate_pa = 1;
    }).toThrow(TypeError);
  });

  it("have behaviour only in the contract, and only about its own amounts", () => {
    expect(ownNames(MarketData)).toEqual([]);
    expect(ownNames(BankCreditData)).toEqual([]);
    expect(new Set(ownNames(ContractData))).toEqual(new Set(["requiredDownPayment", "upfront", "remainingDownPayment"]));
  });

  it("let the contract derive its own amounts", () => {
    expectApprox(C.requiredDownPayment, 88_000);
    expectApprox(C.upfront, 13_000);
    expectApprox(C.remainingDownPayment, 75_000);
    expect(replace(C, { cash_upfront: 100_000 }).remainingDownPayment).toBe(0); // never negative
  });

  it("have unique field names, each routed to its DTO", () => {
    const names = [C, M, B].flatMap((dto) => Object.keys(dto));
    expect(names).toHaveLength(16);
    expect(new Set(names).size).toBe(16);
    expect(fieldNames()).toEqual(names);
    expect(INPUT_GROUPS).toEqual([ContractData, MarketData, BankCreditData]);
    expect(FIELD_OWNER.list_price).toBe(ContractData);
    expect(FIELD_OWNER.incc_rate_pa).toBe(MarketData);
    expect(FIELD_OWNER.pro_soluto_months).toBe(BankCreditData);
    expect(fieldDefaults().incc_rate_pa).toBe(7.0);
    expect("list_price" in fieldDefaults()).toBe(false);
  });

  it("keep the balloon months as a frozen copy (Python normalised them to a tuple)", () => {
    const months = [3, 1];
    const contract = new ContractData({ name: "X", list_price: 1, months_remaining: 1, balloon_months: months });
    months.push(7);
    expect(contract.balloon_months).toEqual([3, 1]);
    expect(Object.isFrozen(contract.balloon_months)).toBe(true);
  });
});

// ----- the interface -----------------------------------------------------------------------------
describe("the interface", () => {
  it("is pure: only the two methods, no data (an interface holds neither at run time)", () => {
    expectTypeOf<keyof SimulationInputInterface>().toEqualTypeOf<"validate" | "withOverrides">();
    expectTypeOf<SimulationInputInterface["validate"]>().toBeFunction();
    expectTypeOf<SimulationInputInterface["withOverrides"]>().toBeFunction();
    expectTypeOf<SimulationInputInterface["withOverrides"]>().parameter(0).toEqualTypeOf<FlatInput>();
  });

  it("has an abstract validator base", () => {
    expect(() => {
      // @ts-expect-error: Validator is abstract
      new Validator();
    }).toThrow(TypeError);
  });
});

// ----- SimulationInput: a frozen composition of the three DTOs ------------------------------------
describe("SimulationInput", () => {
  it("is a frozen composition of the three DTOs", () => {
    expectTypeOf(ra).toExtend<SimulationInputInterface>();
    expect(Object.isFrozen(ra)).toBe(true);
    expect(Object.keys(ra)).toEqual(["contract", "market", "bank_credit"]);
    expect(ra.contract).toBe(C);
    expect(ra.market).toStrictEqual(new MarketData());
    expect(ra.bank_credit).toStrictEqual(new BankCreditData());
    expect(ra).toStrictEqual(new SimulationInput(C, new MarketData(), new BankCreditData()));
    expect(JSON.stringify(ra.toDict())).toBe(JSON.stringify(new SimulationInput(C).toDict()));
    expect(ra.validate()).toBe(ra);
  });

  it("routes each field of the flat form to its DTO", () => {
    const built = SimulationInput.fromDict({
      name: "RA", list_price: 440_000, months_remaining: 19, fgts_upfront: 13_000, developer_installment: 2_500,
      balloon_months: [6, 12], incc_rate_pa: 7.0, pro_soluto_months: 12,
    });
    expect(built).toStrictEqual(ra);
    expect(SimulationInput.fromDict(ra.toDict())).toStrictEqual(ra);
    expect(new Set(Object.keys(ra.toDict()))).toEqual(new Set(fieldNames()));
  });

  it("rejects unknown fields", () => {
    const build = () => SimulationInput.fromDict({ name: "X", list_price: 1, months_remaining: 1, price: 1, colour: "red" });
    expect(build).toThrow(InputShapeError);
    expect(build).toThrow("unknown simulation input field(s): colour, price");
    // not a Python case: a plain object's inherited names are not fields
    expect(() => SimulationInput.fromDict({ ...ra.toDict(), toString: 1 })).toThrow(InputShapeError);
    expect(() => ra.withOverrides({ constructor: 1 })).toThrow(InputShapeError);
  });

  it("crosses DTO boundaries with overrides, and keeps the original", () => {
    const changed = ra.withOverrides({ cash_upfront: 30_000, incc_rate_pa: 4.0, pro_soluto_months: 24 });
    expect([changed.contract.cash_upfront, changed.market.incc_rate_pa, changed.bank_credit.pro_soluto_months]).toEqual([30_000, 4.0, 24]);
    expect(changed.contract.name === "RA" && changed.market.bank_rate_pa === 10.26).toBe(true);
    expect([ra.contract.cash_upfront, ra.market.incc_rate_pa, ra.bank_credit.pro_soluto_months]).toEqual([0, 7.0, 12]);
    expect(ra.withOverrides({ name: "F" })).not.toStrictEqual(ra);
    expect(() => ra.withOverrides({ nonsense: 1 })).toThrow(InputShapeError);
  });
});

// ----- each validator, in isolation, on the DTO it needs -----------------------------------------
describe("each validator", () => {
  type Case = [Validator<never>, ContractData | MarketData | BankCreditData, string];
  const cases: Case[] = [
    [new PropertyValidator(), replace(C, { list_price: 0 }), "list price must be greater than zero"],
    [new PropertyValidator(), replace(C, { list_price: -1 }), "list price must be greater than zero"],
    [new PropertyValidator(), replace(C, { months_remaining: 0 }), "months remaining until delivery must be at least 1"],
    [new PropertyValidator(), replace(C, { down_payment_pct: -10 }), "down payment percentage must be between 0 and 100"],
    [new PropertyValidator(), replace(C, { down_payment_pct: 150 }), "down payment percentage must be between 0 and 100"],
    [new UpfrontPaymentsValidator(), replace(C, { fgts_upfront: -1 }), "upfront payments must not be negative"],
    [new UpfrontPaymentsValidator(), replace(C, { cash_upfront: -1 }), "upfront payments must not be negative"],
    [new UpfrontPaymentsValidator(), replace(C, { cash_upfront: 500_000 }),
      "upfront payments of R$ 513,000.00 exceed the list price of R$ 440,000.00"],
    [new UpfrontPaymentsValidator(), replace(C, { fgts_upfront: 300_000, cash_upfront: 140_000.01 }),
      "upfront payments of R$ 440,000.01 exceed the list price"],
    [new DeveloperPlanValidator(), replace(C, { developer_installment: -1 }), "the monthly developer installment must not be negative"],
    [new DeveloperPlanValidator(), replace(C, { balloon_months: [0] }), "balloon month 0 must be at least 1"],
    [new DeveloperPlanValidator(), replace(C, { balloon_months: [24] }), "balloon month 24 is after delivery (month 19)"],
    [new DeveloperPlanValidator(), replace(C, { balloon_months: [6, 6] }), "balloon months must not repeat"],
    [new MarketRatesValidator(), replace(M, { incc_rate_pa: -100 }), "INCC rate must be greater than -100% per year"],
    [new MarketRatesValidator(), replace(M, { incc_rate_pa: -250 }), "INCC rate must be greater than -100% per year"],
    [new MarketRatesValidator(), replace(M, { bank_rate_pa: -0.01 }), "bank interest rate must not be negative"],
    [new FinancingValidator(), replace(M, { term_months: 0 }), "financing term must be at least 1 month"],
    [new FinancingValidator(), replace(M, { income_commitment_ratio: 0 }), "income commitment ratio must be between 0 and 1"],
    [new FinancingValidator(), replace(M, { income_commitment_ratio: 1.5 }), "income commitment ratio must be between 0 and 1"],
    [new ClosingCostsValidator(), replace(M, { itbi_pct: -3 }), "closing cost percentages must not be negative"],
    [new ClosingCostsValidator(), replace(M, { registry_pct: -1 }), "closing cost percentages must not be negative"],
    [new BankCreditValidator(), replace(B, { pre_approved_credit: -1000 }), "pre-approved credit must not be negative"],
    [new BankCreditValidator(), replace(B, { pro_soluto_months: 0 }), "pro-soluto term must be at least 1 month"],
  ];

  it.each(cases.map(([v, data, message]) => [v.constructor.name, message, v, data] as const))(
    "%s rejects its own rule: %s",
    (_name, message, validator, data) => {
      const run = () => validator.validate(data as never);
      expect(run).toThrow(SimulationError);
      expect(run).toThrow(message);
    },
  );

  const valid: [Validator<never>, ContractData | MarketData | BankCreditData][] = [
    ...DEFAULT_POLICY.contract.validators.map((v) => [v, C] as [Validator<never>, ContractData]),
    ...DEFAULT_POLICY.market.validators.map((v) => [v, M] as [Validator<never>, MarketData]),
    ...DEFAULT_POLICY.bank_credit.validators.map((v) => [v, B] as [Validator<never>, BankCreditData]),
  ];
  it.each(valid.map(([v, data]) => [v.constructor.name, v, data] as const))("%s accepts valid data", (_name, validator, data) => {
    expect(() => validator.validate(data as never)).not.toThrow();
  });

  it.each([
    { incc_rate_pa: -2.0 }, // deflation is a valid, if unusual, market
    { incc_rate_pa: 0.0 },
    { bank_rate_pa: 0.0 },
    { down_payment_pct: 0.0 },
    { down_payment_pct: 100.0 },
    { pre_approved_credit: 0.0 },
    { fgts_upfront: 0.0, cash_upfront: 440_000.0, developer_installment: null, balloon_months: [] }, // cash purchase
    { developer_installment: 0.0, balloon_months: [6] },
    { developer_installment: null, balloon_months: [] },
  ])("accepts the boundary value %j", (overrides) => {
    expect(() => ra.withOverrides(overrides).validate()).not.toThrow();
  });

  it("needs nothing but its DTO", () => {
    new MarketRatesValidator().validate(M); // no SimulationInput anywhere
    expect(() => new PropertyValidator().validate(replace(C, { list_price: 0 }))).toThrow(SimulationError);
    // A market validator cannot be handed the contract or the whole input: the type checker refuses.
    const misuse = () => {
      // @ts-expect-error: a MarketData validator given a SimulationInput
      new MarketRatesValidator().validate(ra);
      // @ts-expect-error: a MarketData validator given a ContractData
      new MarketRatesValidator().validate(C);
    };
    expect(misuse).toBeTypeOf("function");
  });
});

// ----- composition -------------------------------------------------------------------------------
describe("composition", () => {
  it("runs in order and stops at the first error", () => {
    const bothBroken = replace(C, { list_price: 0, cash_upfront: -1 });
    expect(() => DEFAULT_POLICY.contract.validate(bothBroken)).toThrow("list price must be greater than zero");
    const reversedOrder = new CompositeValidator([new UpfrontPaymentsValidator(), new PropertyValidator()]);
    expect(() => reversedOrder.validate(bothBroken)).toThrow("upfront payments must not be negative");
  });

  it("puts every validator in the default policy, under the right DTO", () => {
    const types = (validators: readonly object[]) => new Set(validators.map((v) => v.constructor));
    expect(types(DEFAULT_POLICY.contract.validators)).toEqual(new Set([PropertyValidator, UpfrontPaymentsValidator, DeveloperPlanValidator]));
    expect(types(DEFAULT_POLICY.market.validators)).toEqual(new Set([MarketRatesValidator, FinancingValidator, ClosingCostsValidator]));
    expect(types(DEFAULT_POLICY.bank_credit.validators)).toEqual(new Set([BankCreditValidator]));
  });

  it("checks the contract before the market before the bank credit", () => {
    const everythingBroken = ra.withOverrides({ list_price: 0, bank_rate_pa: -5, pro_soluto_months: 0 });
    expect(() => everythingBroken.validate()).toThrow("list price");
    expect(() => everythingBroken.withOverrides({ list_price: 440_000 }).validate()).toThrow("bank interest rate");
    expect(() => everythingBroken.withOverrides({ list_price: 440_000, bank_rate_pa: 10.26 }).validate()).toThrow("pro-soluto");
  });

  it("accepts a custom policy", () => {
    class Forbidding extends Validator<unknown> {
      validate(): void {
        throw new SimulationError("nope");
      }
    }
    const acceptAll = new CompositeValidator<unknown>([]);
    expect(() => ra.validate(new ValidationPolicy(acceptAll, new Forbidding(), acceptAll))).toThrow("nope");
    expect(ra.validate(new ValidationPolicy(acceptAll, acceptAll, acceptAll))).toBe(ra);
  });
});
