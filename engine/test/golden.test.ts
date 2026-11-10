/**
 * G1's main check: this engine gives the golden master's answers, to the bit, on every case
 * (engine/golden/README.md). They are the retired Python engine's, except those changed on purpose
 * through `npm run golden:update` (listed in that README). Bit-exactness needs a JavaScript engine whose
 * `**` is CPython's: V8 >= 13.6, i.e. Node >= 24 (Node 22 differs in the last bit of ~10 % of powers).
 */
import { describe, expect, it } from "vitest";
import { RUNTIME, corpus, difference, expected, powMismatches, powProbes } from "./golden.js";

describe("golden master", () => {
  it("pairs every case of the corpus with an expected answer", () => {
    expect(corpus.length).toBeGreaterThan(400);
    expect(expected.map((e) => e.id)).toEqual(corpus.map((c) => c.id));
    expect(corpus.map((c) => c.id)).toEqual(corpus.map((_, i) => i));
  });

  it(`runs where ** is CPython's to the last bit (${RUNTIME})`, () => {
    expect(
      powMismatches.length,
      `${powMismatches.length} of ${powProbes.length} powers differ from CPython's in ${RUNTIME}: ` +
        "the golden master needs Node >= 24 (see .nvmrc). The figures still agree to the cent.",
    ).toBe(0);
  });

  const sources = [...new Set(corpus.map((c) => c.source))];
  it.each(sources)("gives the expected answer to every %s case", (source) => {
    const cases = corpus.filter((c) => c.source === source);
    const failures: string[] = [];
    for (const c of cases) {
      const diff = difference(c, expected[c.id]!);
      if (diff) failures.push(`#${c.id} ${c.kind}${c.note ? ` (${c.note})` : ""}: ${diff}`);
    }
    const hint = powMismatches.length ? `\n(${RUNTIME}'s ** differs from CPython's: see the test above)` : "";
    expect(failures, `${failures.length} of ${cases.length} ${source} cases differ:\n${failures.slice(0, 10).join("\n")}${hint}`).toEqual([]);
  });
});
