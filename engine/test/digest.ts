/**
 * The golden master's digest: SHA-256 over the exact bits of a reply. The same function as
 * `feed`/`digest` in engine/golden/tools/from_python.py, which computed the expected digests:
 *
 *   null          "N"           (undefined is an error: JSON would drop it, so it is not None)
 *   boolean       "T" | "F"
 *   number        "D" + IEEE-754 big-endian double (-0 folded into 0; Python ints are doubles here)
 *   string        "S" + uint32 byte length + UTF-8
 *   array         "L" + uint32 length + each item
 *   object        "M" + uint32 key count + each key (sorted) and value
 *
 * Keys are sorted by UTF-16 code unit here and by code point in Python: the same order for the
 * ASCII keys of the payload.
 */
import { createHash } from "node:crypto";
import type { Hash } from "node:crypto";

const utf8 = new TextEncoder();

function u32(n: number): Buffer {
  const b = Buffer.alloc(4);
  b.writeUInt32BE(n);
  return b;
}

function feed(h: Hash, x: unknown): void {
  if (x === undefined) throw new TypeError("undefined in a reply: JSON would drop the key, Python had None");
  if (x === null) h.update("N");
  else if (typeof x === "boolean") h.update(x ? "T" : "F");
  else if (typeof x === "number") {
    const b = Buffer.alloc(9);
    b.write("D");
    b.writeDoubleBE(x === 0 ? 0 : x, 1);
    h.update(b);
  } else if (typeof x === "string") {
    const s = utf8.encode(x);
    h.update(Buffer.concat([Buffer.from("S"), u32(s.length), s]));
  } else if (Array.isArray(x)) {
    h.update(Buffer.concat([Buffer.from("L"), u32(x.length)]));
    for (const v of x) feed(h, v);
  } else if (typeof x === "object") {
    const o = x as Record<string, unknown>;
    const keys = Object.keys(o).sort();
    h.update(Buffer.concat([Buffer.from("M"), u32(keys.length)]));
    for (const k of keys) {
      feed(h, k);
      feed(h, o[k]);
    }
  } else throw new TypeError(`cannot digest a ${typeof x}`);
}

export function digest(reply: unknown): string {
  const h = createHash("sha256");
  feed(h, reply);
  return h.digest("hex");
}
