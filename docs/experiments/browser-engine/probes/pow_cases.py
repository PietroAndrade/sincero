"""
Does JavaScript's `**` give CPython's `**` (C `pow()`, glibc here) to the last bit? The engine's INCC
and bank factors are `(1 + r/100) ** (1/12) - 1` and `(1 + m) ** k`. Writes 200,000 seeded cases
with CPython's answers; probes/pow.mjs replays them in a JavaScript engine.

    python3 probes/pow_cases.py > /tmp/pow_cases.json && node probes/pow.mjs /tmp/pow_cases.json
"""
import json
import random

r = random.Random(1)
cases = []
for _ in range(200_000):
    rate = r.uniform(-20, 30)
    m = (1 + rate / 100) ** (1 / 12) - 1
    k = r.randint(1, 420)
    cases.append([rate, k, (1 + m) ** k, m])
print(json.dumps(cases))
