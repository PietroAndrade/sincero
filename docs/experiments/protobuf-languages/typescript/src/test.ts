/**
 * Small tests pinning the findings of docs/protobuf-languages.md for TypeScript:
 * what the generated code gives, what the proto3 JSON mapping accepts, what `resolve` adds,
 * and what `protovalidate` rules in the .proto enforce.     npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { create, fromBinary, fromJson, isFieldSet, toBinary, toJson, type JsonValue } from "@bufbuild/protobuf";
import { SimulationInputSchema, type SimulationInput } from "./gen/sincero/simulation_input_pb.js";
import { FIELDS, parse, resolve, split, requiredDownPayment, remainingDownPayment, DEFAULT_NAME } from "./experiment.js";
import { violations } from "./rules.js";
import { ValidatedInputSchema } from "./gen/sincero_rules_pb.js";

const RA = { name: "RA", list_price: 440000, months_remaining: 19, fgts_upfront: 13000, developer_installment: 2500, balloon_months: [6, 12] };

test("the generated type is the DTO: a plain object, camelCase, optional fields undefined when absent", () => {
  const ra = fromJson(SimulationInputSchema, RA);
  const typed: SimulationInput = ra;                       // compiles: the message type is a structural type
  assert.equal(typed.listPrice, 440000);
  assert.equal(typed.developerInstallment, 2500);
  assert.equal(typed.inccRatePa, undefined);               // `optional` + omitted -> undefined, not 0
  assert.deepEqual(typed.balloonMonths, [6, 12]);
  assert.equal(requiredDownPayment(resolve(ra)), 88000);
  assert.equal(remainingDownPayment(resolve(ra)), 75000);
});

test("the .proto's defaults, groups and nullability are readable from the custom option", () => {
  const byName = Object.fromEntries(FIELDS.map((f) => [f.name, f]));
  assert.equal(FIELDS.length, 16);
  assert.equal(byName.down_payment_pct.default, 20);
  assert.equal(byName.term_months.default, 360);
  assert.equal(byName.developer_installment.nullable, true);
  assert.equal(byName.list_price.required, true);
  assert.deepEqual(Object.keys(split(resolve(fromJson(SimulationInputSchema, RA)))), ["contract", "market", "bank_credit"]);
});

test("resolve applies the defaults and reports missing required fields", () => {
  const r = resolve(fromJson(SimulationInputSchema, { list_price: 440000, months_remaining: 19 }));
  assert.equal(r.downPaymentPct, 20);
  assert.equal(r.inccRatePa, 7);
  assert.equal(r.name, DEFAULT_NAME);
  assert.equal(r.developerInstallment, undefined);         // nullable stays absent
  assert.throws(() => resolve(fromJson(SimulationInputSchema, { list_price: 440000 })), /months_remaining is required/);
  assert.throws(() => resolve(fromJson(SimulationInputSchema, { list_price: 0, months_remaining: 19 })), /list_price is required/,
    "implicit presence: 0 is indistinguishable from absent");
});

test("proto3 JSON mapping: what it refuses that the contract refuses", () => {
  for (const body of [[1, 2], { list_price: true, months_remaining: 19 }, { list_price: 440000, months_remaining: 19.5 },
                      { list_price: 440000, months_remaining: true }, { list_price: 440000, months_remaining: 19, foo: 1 },
                      { list_price: 440000, months_remaining: 2 ** 31 }, { list_price: 440000, months_remaining: 19, balloon_months: [6, 6.5] },
                      { list_price: 440000, months_remaining: 19, balloon_months: [6, null] }])
    assert.equal(parse(body).ok, false, JSON.stringify(body));
});

test("proto3 JSON mapping: what it accepts that the contract refuses", () => {
  const accepted = (body: unknown) => { const r = parse(body); assert.equal(r.ok, true, JSON.stringify(body)); return (r as any).value as SimulationInput; };
  assert.equal(accepted({ list_price: "440000", months_remaining: 19 }).listPrice, 440000);      // strings are numbers
  assert.equal(accepted({ list_price: 440000, months_remaining: "19" }).monthsRemaining, 19);
  assert.equal(accepted({ listPrice: 440000, monthsRemaining: 19 }).listPrice, 440000);          // camelCase alias
  assert.equal(accepted({ list_price: 440000, months_remaining: 19, itbi_pct: null }).itbiPct, 2); // null = unset = default
  assert.ok(Number.isNaN(accepted({ list_price: "NaN", months_remaining: 19 }).listPrice));       // the quoted NaN
  assert.equal(accepted({ list_price: 440000, months_remaining: 5000 }).monthsRemaining, 5000);  // no API limits
  assert.deepEqual(accepted({ list_price: 440000, months_remaining: 19, balloon_months: [6, "12"] }).balloonMonths, [6, 12]);
});

test("the wire stays snake_case", () => {
  const json = toJson(SimulationInputSchema, resolve(fromJson(SimulationInputSchema, RA)), { useProtoFieldName: true });
  assert.deepEqual(Object.keys(json as object).slice(0, 3), ["name", "list_price", "months_remaining"]);
  assert.equal(Object.keys(toJson(SimulationInputSchema, fromJson(SimulationInputSchema, RA)) as object)[1], "listPrice"); // the default
});

test("validation rules declared in the .proto are enforced (protovalidate)", () => {
  assert.deepEqual(violations({ listPrice: 440000, monthsRemaining: 19, fgtsUpfront: 13000, balloonMonths: [6, 12] }), []);
  assert.deepEqual(violations({ listPrice: 0, monthsRemaining: 0 }),
    ["list_price: must be greater than 0", "months_remaining: must be greater than or equal to 1 and less than or equal to 600"]);
  assert.deepEqual(violations({ listPrice: 440000, monthsRemaining: 19, fgtsUpfront: 300000, cashUpfront: 140001 }),
    ["(message): upfront payments exceed the list price"]);
  assert.deepEqual(violations({ listPrice: 440000, monthsRemaining: 19, balloonMonths: [6, 6, 0] }),
    ["balloon_months: repeated value must contain unique items", "balloon_months.[2]: must be greater than or equal to 1"]);
});

test("a required field absent is refused as required, and 0 as out of range (optional + required)", () => {
  const json = (body: Record<string, unknown>) => violations(fromJson(ValidatedInputSchema, body as JsonValue));
  assert.deepEqual(json({}), ["list_price: value is required", "months_remaining: value is required"]);
  assert.deepEqual(json({ list_price: 440000, months_remaining: null }), ["months_remaining: value is required"]);
  assert.deepEqual(json({ list_price: 440000, months_remaining: 0 }),
    ["months_remaining: must be greater than or equal to 1 and less than or equal to 600"]);
  assert.deepEqual(json({ months_remaining: 19, fgts_upfront: 13000 }), ["list_price: value is required"]);   // CEL quiet
  const zero = create(ValidatedInputSchema, { listPrice: 440000, monthsRemaining: 0 });
  const back = fromBinary(ValidatedInputSchema, toBinary(ValidatedInputSchema, zero));
  assert.equal(isFieldSet(back, ValidatedInputSchema.field.monthsRemaining), true);   // 0 survives the binary wire
});
