/**
 * Experiment: the model's validation rules declared in the .proto (`proto/sincero_rules.proto`,
 * `buf.validate` constraints + one CEL expression) and enforced by `@bufbuild/protovalidate`.
 */
import { create, type MessageInitShape } from "@bufbuild/protobuf";
import { createValidator } from "@bufbuild/protovalidate";
import { ValidatedInputSchema, type ValidatedInput } from "./gen/sincero_rules_pb.js";

const validator = createValidator();

export function violations(input: MessageInitShape<typeof ValidatedInputSchema>): string[] {
  const result = validator.validate(ValidatedInputSchema, create(ValidatedInputSchema, input));
  return result.kind === "valid" || !result.violations ? [] : result.violations.map((v) =>
    `${v.field.map((f) => ("name" in f ? f.name : "index" in f ? `[${f.index}]` : `[${String(f.key)}]`)).join(".") || "(message)"}: ${v.message}`);
}

if (process.argv[1]?.endsWith("rules.js")) {
  const cases: [string, MessageInitShape<typeof ValidatedInputSchema>][] = [
    ["RA", { listPrice: 440000, monthsRemaining: 19, fgtsUpfront: 13000, balloonMonths: [6, 12] }],
    ["list price 0, months 0", { listPrice: 0, monthsRemaining: 0 }],
    ["months 5000", { listPrice: 440000, monthsRemaining: 5000 }],
    ["down payment 150 %", { listPrice: 440000, monthsRemaining: 19, downPaymentPct: 150 }],
    ["repeated balloon, balloon 0", { listPrice: 440000, monthsRemaining: 19, balloonMonths: [6, 6, 0] }],
    ["upfront above the price (CEL)", { listPrice: 440000, monthsRemaining: 19, fgtsUpfront: 300000, cashUpfront: 140001 }],
  ];
  for (const [label, input] of cases) {
    const v = violations(input);
    console.log(`# ${label}\n  ${v.length ? v.join("\n  ") : "valid"}`);
  }
}
