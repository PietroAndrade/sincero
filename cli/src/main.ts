/**
 * The command line (app/controllers/cli_controller.py):
 *
 *     sincero                                          # the five reference properties
 *     sincero --price 440000 --months 19 --fgts 13000 --installment 2500 --balloon-month 6 --balloon-month 12
 *                                   (--months = months REMAINING until delivery)
 *     sincero --price 440000 --months 19 --cash-ladder 0,30000,100000
 *     sincero --price 440000 --months 19 --itbi 3 --registry 1 --income-ratio 0.35
 *     sincero --price 440000 --months 19 --json        # the full JSON payload
 *
 * Exit codes, as cli.py's: 0; 2 when a business rule rejects the input ("error: <message>" on
 * stdout, as cli.py printed it) or when the command line is malformed (usage on stderr).
 */
import {
  SimulationError,
  cashLadder,
  compare,
  inputFromDict,
  simulate,
  simulationToDict,
  whatIfToDict,
} from "@sincero/engine";
import type { SimulationInput } from "@sincero/engine";
import { UsageError, helpText, ladderAmounts, parseArgs, usageLine } from "./flags.js";
import { comparisonTable, ladderTable, report } from "./text-view.js";

export interface Io {
  out(text: string): void;
  err(text: string): void;
}

export const REFERENCE_PROPERTIES: readonly [string, number, number][] = [
  ["SO", 300_000, 4],
  ["F", 396_000, 8],
  ["SV", 233_000, 17],
  ["F4", 320_400, 19],
  ["RA", 440_000, 19],
];

export function runReference(): string {
  const results = compare(
    REFERENCE_PROPERTIES.map(([name, list_price, months_remaining]) =>
      inputFromDict({ name, list_price, months_remaining, fgts_upfront: 13_000 }),
    ),
  );
  const parts = [
    "=== REFERENCE PROPERTIES: 20% down payment, R$ 13,000 FGTS upfront ===",
    "",
    comparisonTable(results),
    "",
    ...results.map((r) => `${report(r)}\n`),
  ];
  return parts.join("\n");
}

export function runCashLadder(input: SimulationInput, amounts: number[], asJson: boolean): string {
  const ladder = whatIfToDict(cashLadder(input, amounts));
  return asJson ? JSON.stringify(ladder, null, 2) : ladderTable(ladder);
}

export function main(argv: readonly string[], io: Io): number {
  const parsed = parseArgs(argv);
  if (parsed.kind === "help") {
    io.out(helpText());
    return 0;
  }
  if (parsed.kind === "usage-error") {
    io.err(`${usageLine()}\nsincero: error: ${parsed.message}\n`);
    return 2;
  }
  const { fields, cashLadder: ladder, json } = parsed;
  if (fields.list_price === undefined) {
    io.out(`${runReference()}\n`); // as cli.py: without --price, the reference run, whatever else was given
    return 0;
  }
  if (fields.months_remaining === undefined) {
    io.err(`${usageLine()}\nsincero: error: --months is required with --price\n`);
    return 2;
  }
  try {
    const input = inputFromDict(fields);
    if (ladder) io.out(`${runCashLadder(input, ladderAmounts(ladder), json)}\n`);
    else {
      const result = simulate(input);
      io.out(`${json ? JSON.stringify(simulationToDict(result), null, 2) : report(result)}\n`);
    }
  } catch (e) {
    if (e instanceof SimulationError) {
      io.out(`error: ${e.message}\n`);
      return 2;
    }
    if (e instanceof UsageError) {
      io.err(`${usageLine()}\nsincero: error: ${e.message}\n`);
      return 2;
    }
    throw e;
  }
  return 0;
}
