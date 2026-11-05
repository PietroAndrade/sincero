/**
 * Experiment: how much is needed to use `backend/proto/sincero/simulation_input.proto` from
 * TypeScript — with the generated code as the DTO, the proto3 JSON mapping as the parser, and
 * the `(sincero.field)` option as the source of defaults and grouping.
 *
 *     npm install && npm run generate && npm run experiment
 *
 * Toolchain: `@bufbuild/buf` (protoc replacement, a binary inside the npm package — no protoc,
 * no Python), `@bufbuild/protoc-gen-es` (code generator), `@bufbuild/protobuf` (runtime).
 */
import { create, fromJson, toJson, isFieldSet, getOption, type DescField } from "@bufbuild/protobuf";
import { SimulationInputSchema, ComparisonRequestSchema, Group, field as fieldOption,
         type SimulationInput } from "./gen/sincero/simulation_input_pb.js";

// ----- 1. the DTO: the generated type itself ---------------------------------------------------
// `SimulationInput` is a plain object type (camelCase properties, `?:` on `optional` fields).
// Nothing to generate on top of it; derived amounts are functions over the type.
// `listPrice` is `number | undefined` now (explicit presence): client code checks it, protovalidate refuses it server-side.
const present = (n: number | undefined, name: string): number => {
  if (n === undefined) throw new Error(`${name} is required`);
  return n;
};
export const requiredDownPayment = (c: SimulationInput) => present(c.listPrice, "list_price") * (c.downPaymentPct ?? 20) / 100;
export const upfront = (c: SimulationInput) => (c.fgtsUpfront ?? 0) + (c.cashUpfront ?? 0);
export const remainingDownPayment = (c: SimulationInput) => Math.max(0, requiredDownPayment(c) - upfront(c));

// ----- 2. what the .proto says about each field, read at runtime from the custom option ---------
export type FieldInfo = { name: string; group: keyof typeof GROUP_NAMES; required: boolean;
                          nullable: boolean; default: unknown; field: DescField };
const GROUP_NAMES = { [Group.CONTRACT]: "contract", [Group.MARKET]: "market", [Group.BANK_CREDIT]: "bank_credit" } as const;

export const FIELDS: FieldInfo[] = SimulationInputSchema.fields.map((f) => {
  const meta = getOption(f, fieldOption);                   // (sincero.field) — typed as FieldMeta
  const dflt = meta.default.case === undefined ? undefined : meta.default.value;
  return { name: f.name, group: meta.group as keyof typeof GROUP_NAMES, field: f,
           required: f.fieldKind !== "list" && (f.presence !== 1 /* EXPLICIT */ || (meta.default.case === undefined && !meta.nullable)),   // a plain scalar, or `optional` with no meaning for omission
           nullable: meta.nullable, default: f.fieldKind === "list" ? [] : dflt };
});

// ----- 3. resolve: defaults applied, required fields checked — the only glue the DTO needs -------
export const DEFAULT_NAME = "CUSTOM";   // the controllers' label for an unnamed input (api-contract, open question)

export function resolve(input: SimulationInput): SimulationInput {
  const out = create(SimulationInputSchema, input);
  for (const info of FIELDS) {
    const set = isFieldSet(out, info.field);                 // implicit presence: `list_price: 0` reads as unset
    if (info.name === "name" && !set) { out.name = DEFAULT_NAME; continue; }
    if (info.required && !set) throw new Error(`${info.name} is required`);
    if (!set && info.default !== undefined && !info.nullable) (out as any)[info.field.localName] = info.default;
  }
  return out;
}

// ----- 4. the three DTOs of the Python model, as a runtime split by group -----------------------
export function split(input: SimulationInput) {
  const groups: Record<string, Record<string, unknown>> = { contract: {}, market: {}, bank_credit: {} };
  for (const info of FIELDS) groups[GROUP_NAMES[info.group]][info.name] = (input as any)[info.field.localName];
  return groups;
}

// ----- 5. the contract's JSON bodies through the proto3 JSON mapping -----------------------------
const MINIMAL = { list_price: 440000, months_remaining: 19 };
export const CASES: [string, unknown, string][] = [
  ["body is an array", [1, 2], "400 wrong_type body"],
  ["string for a number", { list_price: "440000", months_remaining: 19 }, "400 wrong_type list_price"],
  ["boolean for a number", { list_price: true, months_remaining: 19 }, "400 wrong_type list_price"],
  ["19.0 for an integer", { list_price: 440000, months_remaining: 19.0 }, "accepted (19)"],
  ["19.5 for an integer", { list_price: 440000, months_remaining: 19.5 }, "400 wrong_type months_remaining"],
  ['"19" for an integer', { list_price: 440000, months_remaining: "19" }, "400 wrong_type months_remaining"],
  ["true for an integer", { list_price: 440000, months_remaining: true }, "400 wrong_type months_remaining"],
  ["two unknown fields", { ...MINIMAL, fgts_upfrnt: 13000, foo: 1 }, "400 unknown_field fgts_upfrnt"],
  ["camelCase alias", { listPrice: 440000, monthsRemaining: 19 }, "400 unknown_field listPrice"],
  ["missing months_remaining", { list_price: 440000 }, "400 missing_field months_remaining"],
  ["null on itbi_pct", { ...MINIMAL, itbi_pct: null }, "400 null_not_allowed itbi_pct"],
  ["null on developer_installment", { ...MINIMAL, developer_installment: null }, "accepted (absent)"],
  ['"NaN" (string)', { list_price: "NaN", months_remaining: 19 }, "400 wrong_type list_price"],
  ["months_remaining 5000", { list_price: 440000, months_remaining: 5000 }, "400 out_of_range months_remaining"],
  ["months_remaining 2**31", { list_price: 440000, months_remaining: 2 ** 31 }, "400 out_of_range months_remaining"],
  ["balloon item 6.5", { ...MINIMAL, balloon_months: [6, 6.5] }, "400 wrong_type balloon_months[1]"],
  ['balloon item "12"', { ...MINIMAL, balloon_months: [6, "12"] }, "400 wrong_type balloon_months[1]"],
  ["balloon item null", { ...MINIMAL, balloon_months: [6, null] }, "400 null_not_allowed balloon_months[1]"],
  ["omitted defaults", { ...MINIMAL }, "accepted; down_payment_pct resolves to 20.0"],
  ["the RA example", { name: "RA", list_price: 440000, months_remaining: 19, fgts_upfront: 13000,
                       developer_installment: 2500, balloon_months: [6, 12] }, "accepted"],
];

export function parse(body: unknown): { ok: true; value: SimulationInput } | { ok: false; error: string } {
  try {
    const msg = fromJson(SimulationInputSchema, body as any, { ignoreUnknownFields: false });
    return { ok: true, value: resolve(msg) };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

function main() {
  console.log("=== the .proto, read through the custom option ===");
  for (const f of FIELDS)
    console.log(`  ${f.name.padEnd(24)} ${GROUP_NAMES[f.group].padEnd(12)} ${f.required ? "required" : f.nullable ? "nullable" : "default " + JSON.stringify(f.default)}`);

  console.log("\n=== POST /api/simulations — proto3 JSON mapping (protobuf-es) vs the contract ===\n");
  for (const [label, body, contract] of CASES) {
    const r = parse(body);
    console.log(`# ${label}\n  contract : ${contract}\n  protobuf : ${r.ok ? "accepted -> " + JSON.stringify(toJson(SimulationInputSchema, r.value, { useProtoFieldName: true })) : r.error}\n`);
  }

  console.log("=== nested: POST /api/comparisons ===");
  const cmp = fromJson(ComparisonRequestSchema, { base: { fgts_upfront: 13000 },
    candidates: [MINIMAL, { list_price: 396000, months_remaining: "19" }] } as any);
  console.log("  candidate[1].months_remaining as a string:", cmp.candidates[1].monthsRemaining, "(accepted, coerced)");

  const ra = parse(CASES[CASES.length - 1][1])!;
  if (ra.ok) {
    console.log("\n=== the RA input as the three DTOs ===");
    console.log(" ", JSON.stringify(split(ra.value)));
    console.log("  required down payment:", requiredDownPayment(ra.value), "remaining:", remainingDownPayment(ra.value));
  }

  const n = 20000, body = CASES[CASES.length - 1][1];
  const t0 = performance.now();
  for (let i = 0; i < n; i++) resolve(fromJson(SimulationInputSchema, body as any));
  console.log(`\n=== timing: fromJson + resolve, the RA body, mean of ${n}: ${((performance.now() - t0) / n * 1000).toFixed(1)} us`);
}

if (process.argv[1] && process.argv[1].endsWith("experiment.js")) main();
