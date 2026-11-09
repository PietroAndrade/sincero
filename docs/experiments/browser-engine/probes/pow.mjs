// Replays probes/pow_cases.py's cases in this JavaScript engine: node probes/pow.mjs /tmp/pow_cases.json
import fs from "node:fs";
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let monthly = 0, power = 0;
for (const [rate, k, pyPow, pyMonthly] of cases) {
  if ((1 + rate / 100) ** (1 / 12) - 1 !== pyMonthly) monthly++;
  if ((1 + pyMonthly) ** k !== pyPow) power++;
}
console.log(`node ${process.version} (V8 ${process.versions.v8}): ${cases.length} cases; ` +
  `(1+r)**(1/12) differs from CPython in ${monthly}, (1+m)**k in ${power}`);
