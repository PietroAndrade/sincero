// Node side of harness/golden_digest.py: the same digest over the TypeScript port (see there).
import { createHash } from "node:crypto";
import fs from "node:fs";
import * as e from "/tmp/eng.mjs";
const enc = new TextEncoder();
function feed(h, x) {
  const u32 = (n) => { const b = Buffer.alloc(4); b.writeUInt32BE(n); return b; };
  if (x === null || x === undefined) h.update("N");
  else if (typeof x === "boolean") h.update(x ? "T" : "F");
  else if (typeof x === "number") { const b = Buffer.alloc(9); b.write("D"); b.writeDoubleBE(x === 0 ? 0 : x, 1); h.update(b); }
  else if (typeof x === "string") { const s = enc.encode(x); h.update(Buffer.concat([Buffer.from("S"), u32(s.length), s])); }
  else if (Array.isArray(x)) { h.update(Buffer.concat([Buffer.from("L"), u32(x.length)])); x.forEach((v) => feed(h, v)); }
  else { const keys = Object.keys(x).sort(); h.update(Buffer.concat([Buffer.from("M"), u32(keys.length)])); for (const k of keys) { feed(h, k); feed(h, x[k]); } }
}
// Python sorts keys by code point; JS default sort is by UTF-16 code unit: the same for these ASCII keys.
const call = (kind, r) => {
  try {
    const value = kind === "simulate" ? e.simulateDict(r.input) : kind === "compare" ? e.compareDicts(r.inputs) : e.cashLadderDict(r.input, r.amounts);
    return { ok: true, value };
  } catch (x) {
    if (x instanceof e.SimulationError) return { ok: false, kind: "rejected", error: x.message };
    if (x instanceof e.InputShapeError) return { ok: false, kind: "invalid_shape", error: "<shape>" };
    throw x;
  }
};
const cases = JSON.parse(fs.readFileSync("/tmp/cases.json"));
const golden = JSON.parse(fs.readFileSync("/tmp/golden.json"));
let same = 0, shape = 0; const bad = [];
cases.forEach((c, i) => {
  const reply = call(c.kind, c.request);
  if (!reply.ok && reply.kind === "invalid_shape") { shape++; return; }  // Python's TypeError text is CPython's own: not digested
  const h = createHash("sha256"); feed(h, reply);
  h.digest("hex") === golden[i].digest ? same++ : bad.push(i);
});
console.log(`node ${process.version}: ${same} of ${cases.length - shape} digests identical (${shape} shape errors skipped); mismatches: ${bad.slice(0, 10)}`);
