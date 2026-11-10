/**
 * The command line (plan item P3.1). Three layers:
 *   - the Python CLI's own output, recorded in fixtures/python-cli.json (README examples, every flag,
 *     errors, half-cent ties), replayed: the text byte for byte, the JSON payloads by digest;
 *   - tests/test_cli_controller.py (5 tests) and test_views.py's text-report test, ported;
 *   - argparse's behaviour the fixtures cannot show (usage errors go to stderr), and the bin itself.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { describe, expect, it } from "vitest";
import { ContractData, SimulationInput, fieldNames, inputFromDict, simulate } from "@sincero/engine";
import { digest } from "../../engine/test/digest.js";
import { FLAGS, parseArgs } from "../src/flags.js";
import { main } from "../src/main.js";
import { report } from "../src/text-view.js";

function run(argv: string[]): { code: number; out: string; err: string } {
  let out = "";
  let err = "";
  const code = main(argv, { out: (t) => (out += t), err: (t) => (err += t) });
  return { code, out, err };
}

interface Fixture {
  note: string;
  argv: string[];
  exit: number;
  stdout?: string;
  json_digest?: string;
}
const fixtures: Fixture[] = JSON.parse(fs.readFileSync(new URL("fixtures/python-cli.json", import.meta.url), "utf8")).cases;

describe("the Python CLI's output, replayed", () => {
  it.each(fixtures.map((f) => [f.note, f] as const))("%s", (_note, f) => {
    const { code, out, err } = run(f.argv);
    expect(err).toBe("");
    expect(code).toBe(f.exit);
    if (f.json_digest !== undefined) expect(digest(JSON.parse(out))).toBe(f.json_digest);
    else expect(out).toBe(f.stdout);
  });
});

describe("test_cli_controller.py", () => {
  const fieldsOf = (argv: string[]) => {
    const parsed = parseArgs(argv);
    if (parsed.kind !== "run") throw new Error(`not a run: ${JSON.stringify(parsed)}`);
    return parsed.fields;
  };

  it("has a flag for every model field", () => {
    expect(new Set(FLAGS.map((f) => f.field))).toEqual(new Set(fieldNames()));
  });

  it("uses the model's defaults", () => {
    const input = inputFromDict(fieldsOf(["--price", "440000", "--months", "19"]));
    expect(input).toStrictEqual(new SimulationInput(new ContractData({ name: "CUSTOM", list_price: 440_000, months_remaining: 19 })));
  });

  it("takes the closing costs, income ratio and pro-soluto flags to the model", () => {
    const input = inputFromDict(
      fieldsOf([
        "--price", "440000", "--months", "19", "--itbi", "3", "--registry", "1", "--income-ratio", "0.35",
        "--pro-soluto-months", "24", "--balloon-month", "6", "--balloon-month", "12", "--installment", "2500",
      ]),
    );
    const { market, bank_credit: credit, contract } = input;
    expect([market.itbi_pct, market.registry_pct, market.income_commitment_ratio, credit.pro_soluto_months]).toEqual([3, 1, 0.35, 24]);
    expect(contract.balloon_months).toEqual([6, 12]);
    expect(contract.developer_installment).toBe(2500);
  });

  it("shows the model's defaults in --help, as Python printed them", () => {
    const { code, out } = run(["--help"]);
    expect(code).toBe(0);
    for (const shown of ["(default: 7.0)", "(default: 0.5)", "(default: 0.3)", "(default: 10.26)", "(default: 360)", "(default: CUSTOM)"])
      expect(out).toContain(shown);
  });

  it("exits with code 2 on an invalid input, the message on stdout", () => {
    const { code, out } = run(["--price", "440000", "--months", "0"]);
    expect(code).toBe(2);
    expect(out).toContain("months remaining until delivery must be at least 1");
  });
});

describe("test_views.py: the text report", () => {
  it("mentions the key figures", () => {
    const ra = inputFromDict({
      name: "RA", list_price: 440_000, months_remaining: 19, fgts_upfront: 13_000, developer_installment: 2_500, balloon_months: [6, 12],
    });
    const text = report(simulate(ra));
    for (const figure of ["R$ 391.802,30", "SAC:", "PRICE:"]) expect(text).toContain(figure);
  });
});

describe("the command line, as argparse read it", () => {
  const usage = (argv: string[]) => {
    const { code, out, err } = run(argv);
    expect([code, out]).toEqual([2, ""]);
    expect(err).toMatch(/^usage: sincero /);
    return err.trimEnd().split("\n").at(-1); // after the (wrapped) usage line
  };

  it("refuses what it cannot read, with a usage line on stderr", () => {
    expect(usage(["--price", "440000", "--months", "19", "--colour", "red"])).toBe("sincero: error: unrecognized arguments: --colour");
    expect(usage(["--price", "abc"])).toBe("sincero: error: argument --price: invalid float value: 'abc'");
    expect(usage(["--price", "440000", "--months", "19.5"])).toBe("sincero: error: argument --months: invalid int value: '19.5'");
    expect(usage(["--price"])).toBe("sincero: error: argument --price: expected one argument");
    expect(usage(["--b", "3"])).toBe("sincero: error: ambiguous option: --b could match --balloon-month, --bank-rate");
    expect(usage(["440000"])).toBe("sincero: error: unrecognized arguments: 440000");
    expect(usage(["--price", "440000", "--cash-ladder", "0,abc"])).toBe("sincero: error: --months is required with --price");
    expect(usage(["--price", "440000", "--months", "19", "--cash-ladder", "0,abc"])).toBe(
      "sincero: error: argument --cash-ladder: invalid amount: 'abc'",
    );
  });

  it("reads a unique prefix of a flag, and Python's number syntax", () => {
    const full = run(["--price", "440000", "--months", "19", "--pre-approved", "300000"]);
    expect(run(["--pri", "4.4e5", "--mon", "19", "--pre", "300_000"])).toEqual(full);
  });

  it("keeps the last value of a repeated flag", () => {
    expect(run(["--price", "1", "--price", "440000", "--months", "19"])).toEqual(run(["--price", "440000", "--months", "19"]));
  });

  it("refuses a cash ladder the engine refuses (P1.6): unsorted amounts, named", () => {
    const { code, out } = run(["--price", "440000", "--months", "19", "--cash-ladder", "30000,0"]);
    expect([code, out]).toEqual([2, "error: cash ladder amounts must increase: R$ 0.00 comes after R$ 30,000.00\n"]);
  });
});

describe("the sincero bin", () => {
  const bin = new URL("../bin/sincero.mjs", import.meta.url).pathname;
  it("prints the report and exits with the CLI's code", () => {
    const ok = spawnSync(process.execPath, [bin, "--price", "440000", "--months", "19", "--fgts", "13000"], { encoding: "utf8" });
    expect(ok.status).toBe(0);
    expect(ok.stdout).toContain("Credit gap at delivery: R$ 39.802,30");
    const rejected = spawnSync(process.execPath, [bin, "--price", "440000", "--months", "0"], { encoding: "utf8" });
    expect(rejected.status).toBe(2);
  }, 60_000); // two processes; the first compiles the TypeScript with nothing cached yet (a fresh clone, CI)
});
