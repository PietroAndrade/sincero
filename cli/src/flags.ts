/**
 * The command line's flags and their parsing (app/controllers/cli_controller.py, which used
 * argparse). Every input field has one flag; no default is repeated here: they come from the
 * engine's FIELDS and are shown in --help.
 *
 * What is kept from argparse: `--flag value` and `--flag=value`, a unique prefix of a flag
 * (`--pre 1` is `--pre-approved 1`), Python's float() and int() syntax for values (`1e5`, `1_000`,
 * `-2`), the last value of a repeated flag, every value of --balloon-month, and exit code 2 with a
 * usage line for a malformed command line.
 */
import { FIELDS } from "@sincero/engine";

type Kind = "str" | "float" | "int";

export interface Flag {
  readonly flag: string;
  readonly field: string;
  readonly kind: Kind;
  readonly help: string;
  readonly repeat?: true;
}

// CLI flag -> input field, in cli.py's order.
export const FLAGS: readonly Flag[] = [
  { flag: "--name", field: "name", kind: "str", help: "label of the property (default: %(default)s)" },
  { flag: "--price", field: "list_price", kind: "float", help: "list price in R$" },
  {
    flag: "--months",
    field: "months_remaining",
    kind: "int",
    help: "months remaining until delivery (time left, not the project's total duration)",
  },
  {
    flag: "--down-payment-pct",
    field: "down_payment_pct",
    kind: "float",
    help: "down payment required by the developer, % of the list price (default: %(default)s)",
  },
  { flag: "--fgts", field: "fgts_upfront", kind: "float", help: "FGTS used at signing, R$ (default: %(default)s)" },
  {
    flag: "--cash",
    field: "cash_upfront",
    kind: "float",
    help: "cash paid at signing, R$; above the down payment it reduces the financed balance (default: %(default)s)",
  },
  {
    flag: "--installment",
    field: "developer_installment",
    kind: "float",
    help: "monthly amount paid to the developer; what it does not cover becomes balloons\n(default: balance / months)",
  },
  {
    flag: "--balloon-month",
    field: "balloon_months",
    kind: "int",
    repeat: true,
    help: "construction month with a balloon payment (repeatable); the amount is derived",
  },
  { flag: "--incc", field: "incc_rate_pa", kind: "float", help: "INCC, % per year (default: %(default)s)" },
  { flag: "--bank-rate", field: "bank_rate_pa", kind: "float", help: "bank interest rate, % per year (default: %(default)s)" },
  { flag: "--term", field: "term_months", kind: "int", help: "bank financing term in months (default: %(default)s)" },
  { flag: "--itbi", field: "itbi_pct", kind: "float", help: "ITBI, % of the list price (default: %(default)s)" },
  {
    flag: "--registry",
    field: "registry_pct",
    kind: "float",
    help: "registry and deed costs, % of the list price (default: %(default)s)",
  },
  {
    flag: "--income-ratio",
    field: "income_commitment_ratio",
    kind: "float",
    help: "max share of household income the bank accepts as installment, 0-1 (default: %(default)s)",
  },
  {
    flag: "--pre-approved",
    field: "pre_approved_credit",
    kind: "float",
    help: "credit pre-approved by the bank at signing, R$ (default: nominal mortgage balance)",
  },
  {
    flag: "--pro-soluto-months",
    field: "pro_soluto_months",
    kind: "int",
    help: "months to pay the developer any credit gap (default: %(default)s)",
  },
];

const CASH_LADDER = "--cash-ladder";
const JSON_FLAG = "--json";
const HELP_FLAGS = ["-h", "--help"];
const ALL_FLAGS = [...FLAGS.map((f) => f.flag), CASH_LADDER, JSON_FLAG, "--help"];

/** `name` is the only field without a model default; the CLI labels an unnamed property CUSTOM. */
export const DEFAULT_NAME = "CUSTOM";

export type Parsed =
  | { kind: "help" }
  | { kind: "usage-error"; message: string }
  | { kind: "run"; fields: Record<string, unknown>; cashLadder: string | null; json: boolean };

export class UsageError extends Error {}

// ----- Python's float() and int() ------------------------------------------------------------------
const DIGITS = String.raw`\d(?:_?\d)*`;
const FLOAT = new RegExp(String.raw`^[+-]?(?:(?:${DIGITS})?\.${DIGITS}|${DIGITS}\.?)(?:[eE][+-]?${DIGITS})?$`);
const INT = new RegExp(String.raw`^[+-]?${DIGITS}$`);
const SPECIAL: Record<string, number> = { inf: Infinity, infinity: Infinity, nan: NaN };

function pyFloat(text: string): number | undefined {
  const s = text.trim();
  const special = SPECIAL[s.replace(/^[+-]/, "").toLowerCase()];
  if (special !== undefined) return s.startsWith("-") ? -special : special;
  return FLOAT.test(s) ? Number(s.replace(/_/g, "")) : undefined;
}

function pyInt(text: string): number | undefined {
  const s = text.trim();
  return INT.test(s) ? Number(s.replace(/_/g, "")) : undefined;
}

const looksNegative = (s: string) => /^-\d|^-\.\d/.test(s);

function value(flag: Flag, text: string): unknown {
  if (flag.kind === "str") return text;
  const parsed = flag.kind === "int" ? pyInt(text) : pyFloat(text);
  if (parsed === undefined) throw new UsageError(`argument ${flag.flag}: invalid ${flag.kind} value: '${text}'`);
  return parsed;
}

/** The flag `arg` names: itself, or the one flag it is a prefix of. */
function resolve(arg: string): string {
  if (ALL_FLAGS.includes(arg)) return arg;
  const candidates = ALL_FLAGS.filter((f) => f.startsWith(arg));
  if (candidates.length === 1) return candidates[0]!;
  if (candidates.length > 1) throw new UsageError(`ambiguous option: ${arg} could match ${candidates.join(", ")}`);
  throw new UsageError(`unrecognized arguments: ${arg}`);
}

export function parseArgs(argv: readonly string[]): Parsed {
  const fields: Record<string, unknown> = {};
  let cashLadder: string | null = null;
  let json = false;
  try {
    for (let i = 0; i < argv.length; i++) {
      const arg = argv[i]!;
      if (HELP_FLAGS.includes(arg)) return { kind: "help" };
      if (!arg.startsWith("-") || looksNegative(arg)) throw new UsageError(`unrecognized arguments: ${arg}`);
      const eq = arg.indexOf("=");
      const name = resolve(eq >= 0 ? arg.slice(0, eq) : arg);
      if (name === "--help") return { kind: "help" };
      if (name === JSON_FLAG) {
        if (eq >= 0) throw new UsageError(`argument --json: ignored explicit argument '${arg.slice(eq + 1)}'`);
        json = true;
        continue;
      }
      let text: string;
      if (eq >= 0) text = arg.slice(eq + 1);
      else {
        const next = argv[i + 1];
        if (next === undefined || (next.startsWith("-") && !looksNegative(next)))
          throw new UsageError(`argument ${name}: expected one argument`);
        text = next;
        i++;
      }
      if (name === CASH_LADDER) {
        cashLadder = text;
        continue;
      }
      const flag = FLAGS.find((f) => f.flag === name)!;
      const parsed = value(flag, text);
      if (flag.repeat) fields[flag.field] = [...((fields[flag.field] as unknown[] | undefined) ?? []), parsed];
      else fields[flag.field] = parsed;
    }
  } catch (e) {
    if (e instanceof UsageError) return { kind: "usage-error", message: e.message };
    throw e;
  }
  return { kind: "run", fields: { name: DEFAULT_NAME, ...fields }, cashLadder, json };
}

/** The cash-ladder amounts: `0,30000,100000`, each a Python float. */
export function ladderAmounts(text: string): number[] {
  return text.split(",").map((part) => {
    const amount = pyFloat(part);
    if (amount === undefined) throw new UsageError(`argument --cash-ladder: invalid amount: '${part}'`);
    return amount;
  });
}

// ----- --help --------------------------------------------------------------------------------------
/** A default as Python printed it: floats with their `.0` (`7.0`), ints without (`360`). */
function pyDefault(flag: Flag, value: unknown): string {
  if (typeof value === "number" && flag.kind === "float" && Number.isInteger(value)) return value.toFixed(1);
  return String(value);
}

/** The usage line, wrapped at 80 columns under its first item, as argparse prints it. */
export function usageLine(): string {
  const parts = ["[-h]", ...FLAGS.map((f) => `[${f.flag} ${metavar(f.flag)}]`), `[${CASH_LADDER} CASH_LADDER]`, `[${JSON_FLAG}]`];
  const head = "usage: sincero ";
  const lines: string[] = [];
  let line = "";
  for (const part of parts) {
    if (line && head.length + line.length + 1 + part.length > 80) {
      lines.push(line);
      line = part;
    } else line = line ? `${line} ${part}` : part;
  }
  lines.push(line);
  return head + lines.join(`\n${" ".repeat(head.length)}`);
}

const metavar = (flag: string) => flag.replace(/^--/, "").toUpperCase().replace(/-/g, "_");

export function helpText(): string {
  const defaults: Record<string, unknown> = Object.fromEntries(FIELDS.map((f) => [f.name, f.default]));
  defaults.name = DEFAULT_NAME;
  const rows: [string, string][] = [["-h, --help", "show this help message and exit"]];
  for (const f of FLAGS) rows.push([`${f.flag} ${metavar(f.flag)}`, f.help.replace("%(default)s", pyDefault(f, defaults[f.field]))]);
  rows.push([`${CASH_LADDER} CASH_LADDER`, "comma-separated cash amounts to compare, e.g. 0,30000,100000"]);
  rows.push([JSON_FLAG, "print the JSON payload instead of the text report"]);
  const width = 24;
  const lines = rows.flatMap(([left, help]) => {
    const [first = "", ...rest] = help.split("\n");
    // argparse: on the flag's line when the flag leaves two spaces before the help column
    const head = left.length <= width - 4 ? `  ${left.padEnd(width - 2)}${first}` : `  ${left}\n${" ".repeat(width)}${first}`;
    return [head, ...rest.map((line) => `${" ".repeat(width)}${line}`)];
  });
  return [usageLine(), "", "SINCERO — off-plan apartment cost simulator (Brazil)", "", "options:", ...lines, ""].join("\n");
}
