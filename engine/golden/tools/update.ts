/**
 * `npm run golden:update`: rewrite the golden master's expected answers from THIS engine, after a
 * change to the figures that a scenario describes (plan item P3.3; the protocol is in
 * engine/README.md and engine/golden/README.md).
 *
 *     npm run golden:update -- --dry-run    list the cases whose answer would change; write nothing
 *     npm run golden:update                 write them into engine/golden/expected.json
 *
 * Only the `cases` section of expected.json is rewritten, one line per case, in the format the
 * Python generator wrote: a case whose answer did not change keeps its line byte for byte, so the
 * diff of the file is the list of changed answers. The header (the oracle, the `**` probes) is kept
 * as it is. A case added at the end of corpus.json (next id, with a `note`) gets its first entry.
 *
 * Refuses to run on a JavaScript engine whose `**` is not CPython's (Node < 24): it would write
 * last-bit differences into the golden master.
 */
import fs from "node:fs";
import type { Expected } from "../../test/golden.js";
import { EXPECTED_FILE, RUNTIME, corpus, describeChange, entryFor, expected, powMismatches, powProbes, quote } from "../../test/golden.js";

const dryRun = process.argv.includes("--dry-run");
const fail = (message: string): never => {
  console.error(`golden:update: ${message}`);
  process.exit(2);
};

if (powMismatches.length)
  fail(`${powMismatches.length} of ${powProbes.length} powers differ from CPython's in ${RUNTIME}. Use Node >= 24 (see .nvmrc).`);
if (corpus.some((c, i) => c.id !== i)) fail("corpus.json: every case's id must be its position (0, 1, 2, …)");
if (expected.length > corpus.length)
  fail(`expected.json has ${expected.length} cases and corpus.json ${corpus.length}: cases are never removed from the corpus`);
if (expected.some((e, i) => e.id !== i)) fail("expected.json: every entry's id must be its position");

const entries: Expected[] = [];
const changes: string[] = [];
for (const c of corpus) {
  let entry: Expected;
  try {
    entry = entryFor(c);
  } catch (e) {
    fail(`case #${c.id} threw ${e instanceof Error ? `${e.name}: ${e.message}` : String(e)}: the engine must answer every case`);
    throw e; // unreachable: fail() exits
  }
  entries.push(entry);
  const before = expected[c.id];
  const change = before === undefined ? `new case: ${quote(entry)}` : describeChange(before, entry);
  if (change) changes.push(`#${c.id} ${c.source} ${c.kind}${c.note ? ` (${c.note})` : ""}: ${change}`);
}

console.log(`${RUNTIME}: ${corpus.length} cases, ${changes.length} changed${changes.length ? ":" : ""}`);
for (const line of changes) console.log(`  ${line}`);
if (dryRun || changes.length === 0) {
  if (dryRun && changes.length) console.log("(dry run: nothing written)");
  process.exit(0);
}

// Keep everything before the cases section as it is; write the cases as the Python generator did.
const text = fs.readFileSync(EXPECTED_FILE, "utf8");
const marker = '\n  "cases": [\n';
const at = text.indexOf(marker);
if (at < 0 || text.indexOf(marker, at + 1) >= 0) fail(`expected.json: cannot find its one "cases" section`);
const lines = entries.map((e) => JSON.stringify(e)).join(",\n    ");
const updated = `${text.slice(0, at)}${marker}    ${lines}\n  ]\n}\n`;
JSON.parse(updated); // well-formed, or fail before writing
fs.writeFileSync(EXPECTED_FILE, updated);
console.log(`written: ${EXPECTED_FILE.pathname}. Review its diff with the change that caused it.`);
