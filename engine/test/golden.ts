/**
 * The golden master (engine/golden/): the corpus, the retired Python engine's answers, and the
 * same question asked of this engine. See engine/golden/README.md.
 */
import fs from "node:fs";
import {
  InputShapeError,
  SimulationError,
  cashLadderDict,
  compareDicts,
  inputFromDict,
  simulateDict,
  whatIf,
  whatIfToDict,
} from "../src/index.js";
import type { FlatInput } from "../src/index.js";
import { digest } from "./digest.js";

export type Case =
  | { id: number; source: string; note?: string; kind: "simulate"; input: FlatInput }
  | { id: number; source: string; note?: string; kind: "compare"; inputs: FlatInput[] }
  | { id: number; source: string; note?: string; kind: "cash_ladder"; input: FlatInput; amounts: number[] }
  | { id: number; source: string; note?: string; kind: "what_if"; input: FlatInput; variations: [string, FlatInput][] };

export type Outcome = "ok" | "rejected" | "invalid_shape";

export interface Expected {
  id: number;
  outcome: Outcome;
  /** The rejection message, verbatim (outcome "rejected"). */
  error?: string;
  /** SHA-256 of the reply (every outcome but "invalid_shape", whose text was CPython's own). */
  digest?: string;
}

export type Reply = { ok: true; value: unknown } | { ok: false; kind: "rejected"; error: string } | { ok: false; kind: "invalid_shape" };

export const CORPUS_FILE = new URL("../golden/corpus.json", import.meta.url);
export const EXPECTED_FILE = new URL("../golden/expected.json", import.meta.url);
const read = (file: URL) => JSON.parse(fs.readFileSync(file, "utf8"));

export const corpus: Case[] = read(CORPUS_FILE).cases;
const expectedFile = read(EXPECTED_FILE);
export const expected: Expected[] = expectedFile.cases;
/** [rate % a year, k, CPython's (1 + rate/100) ** (1/12) - 1, CPython's (1 + monthly) ** k] */
export const powProbes: [number, number, number, number][] = expectedFile.pow_probes;

/** The probes this runtime's `**` gets wrong (none on Node >= 24). */
export const powMismatches = powProbes.filter(
  ([rate, k, monthly, power]) => (1.0 + rate / 100.0) ** (1.0 / 12.0) - 1.0 !== monthly || (1.0 + monthly) ** k !== power,
);
export const RUNTIME = `Node ${process.version} (V8 ${process.versions.v8})`;

/** Ask this engine one case: the payload, or the error it throws. */
export function run(c: Case): unknown {
  switch (c.kind) {
    case "simulate":
      return simulateDict(c.input);
    case "compare":
      return compareDicts(c.inputs);
    case "cash_ladder":
      return cashLadderDict(c.input, c.amounts);
    case "what_if":
      return whatIfToDict(whatIf(inputFromDict(c.input), c.variations));
  }
}

/** This engine's answer to one case, in the shape the Python answers were digested in. */
export function answer(c: Case): Reply {
  try {
    return { ok: true, value: run(c) };
  } catch (e) {
    if (e instanceof SimulationError) return { ok: false, kind: "rejected", error: e.message };
    if (e instanceof InputShapeError) return { ok: false, kind: "invalid_shape" };
    throw e;
  }
}

export const outcomeOf = (r: Reply): Outcome => (r.ok ? "ok" : r.kind);

/** The expected.json entry of this engine's answer, keys in the order the Python writer used. */
export function entryFor(c: Case): Expected {
  const reply = answer(c);
  const entry: Expected = { id: c.id, outcome: outcomeOf(reply) };
  if (!reply.ok && reply.kind === "rejected") entry.error = reply.error;
  if (reply.ok || reply.kind !== "invalid_shape") entry.digest = digest(reply);
  return entry;
}

/** What differs between two entries of the same case, or null when nothing does. */
/** An entry's outcome, with its message when it is a rejection. */
export const quote = (e: Expected): string => `${e.outcome}${e.error !== undefined ? ` ("${e.error}")` : ""}`;

export function describeChange(from: Expected, to: Expected): string | null {
  if (from.outcome !== to.outcome) return `outcome ${quote(to)}, expected ${quote(from)}`;
  if (from.error !== to.error) return `message "${to.error}", expected "${from.error}"`;
  if (from.digest !== to.digest) return "same outcome, different reply (a figure, even in its last bit, a key, a label or a row)";
  return null;
}

/** What differs between this engine's answer to `c` and the expected one, or null when nothing does. */
export function difference(c: Case, exp: Expected): string | null {
  let got: Expected;
  try {
    got = entryFor(c);
  } catch (e) {
    return `threw ${e instanceof Error ? `${e.name}: ${e.message}` : String(e)}`;
  }
  return describeChange(exp, got);
}
