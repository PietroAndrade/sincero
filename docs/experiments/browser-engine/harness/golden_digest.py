"""
Prototype of the golden master that lets the Python engine be retired without losing it as the
oracle: one SHA-256 per corpus case over the reply's exact bits (keys sorted, numbers as IEEE-754
big-endian doubles, -0.0 folded into 0.0). ~34 KB for 429 cases. harness/golden_digest.mjs computes
the same digest over the TypeScript port in Node and compares.

    python harness/golden_digest.py          # writes /tmp/cases.json and /tmp/golden.json
    npx esbuild ../../../engine/src/index.ts --bundle --format=esm --outfile=/tmp/eng.mjs && node harness/golden_digest.mjs

Superseded by the engine package's golden master (engine/golden/, P1.3), which uses the same digest.
"""
import hashlib, json, struct, sys
sys.path.insert(0, "harness")
import corpus

def feed(h, x):
    if x is None: h.update(b"N")
    elif isinstance(x, bool): h.update(b"T" if x else b"F")
    elif isinstance(x, (int, float)):
        x = float(x); x = 0.0 if x == 0 else x            # canonical: -0.0 -> 0.0
        h.update(b"D" + struct.pack(">d", x))
    elif isinstance(x, str):
        b = x.encode(); h.update(b"S" + struct.pack(">I", len(b)) + b)
    elif isinstance(x, list):
        h.update(b"L" + struct.pack(">I", len(x)))
        for v in x: feed(h, v)
    elif isinstance(x, dict):
        h.update(b"M" + struct.pack(">I", len(x)))
        for k in sorted(x): feed(h, k); feed(h, x[k])
    else: raise TypeError(type(x))

def digest(reply):
    h = hashlib.sha256(); feed(h, reply); return h.hexdigest()

cases = corpus.build()
json.dump([{"kind": c["kind"], "request": corpus.request_of(c)} for c in cases], open("/tmp/cases.json", "w"))
golden = [{"digest": digest(corpus.expected(c))} for c in cases]
json.dump(golden, open("/tmp/golden.json", "w"))
print("cases", len(cases), "golden file bytes", len(json.dumps(golden)))
