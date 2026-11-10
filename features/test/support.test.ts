/**
 * The support library's own tests (tests/test_support.py, 10 tests): no cucumber, no engine run.
 * Python's `re.fullmatch(PATTERN, text)` is a match of the pattern anchored at both ends.
 */
import { describe, expect, it } from "vitest";
import { METRIC_PATTERN, STATIC_METRICS, UnknownMetricError, parseMetric } from "../support/metrics.js";
import { MONEY_PATTERN, PERCENT_PATTERN, describeMismatch, isClose, parseMoney, parsePercent } from "../support/money.js";

const fullmatch = (pattern: RegExp, text: string) => new RegExp(`^(?:${pattern.source})$`).test(text);

describe("the support library", () => {
  it.each([
    ["R$ 1,234.56", 1234.56],
    ["1,234.56", 1234.56],
    ["0.00", 0.0],
    ["-3.10", -3.1],
    ["440,000.00", 440000.0],
  ])("parses the money figure %s", (text, value) => {
    expect(parseMoney(text)).toBe(value);
  });

  it("rejects garbage as money", () => {
    expect(() => parseMoney("R$ ")).toThrow(RangeError);
  });

  it.each([
    ["20.0%", 20.0],
    ["18.613", 18.613],
    ["0", 0.0],
  ])("parses the percentage %s", (text, value) => {
    expect(parsePercent(text)).toBe(value);
  });

  it("matches the money figures the features write", () => {
    for (const sample of ["88,000.00", "0.00", "152.26", "1,234,567.89"]) expect(fullmatch(MONEY_PATTERN, sample), sample).toBe(true);
    expect(fullmatch(PERCENT_PATTERN, "18.613")).toBe(true);
  });

  it("compares to half a cent", () => {
    expect(isClose(100.004, 100.0)).toBe(true);
    expect(isClose(100.006, 100.0)).toBe(false);
  });

  it("names the expected and the observed figure in a mismatch", () => {
    expect(describeMismatch("credit gap", 10.0, 12.5)).toBe("credit gap: expected 10.00, observed 12.50 (diff +2.50)");
  });

  it("matches every static metric with the pattern", () => {
    for (const label of Object.keys(STATIC_METRICS)) expect(fullmatch(METRIC_PATTERN, label), label).toBe(true);
  });

  it.each([
    ["credit gap", ["credit_gap", "gap"]],
    ["developer installment in month 3", ["down_payment", "schedule", 2, "installment"]],
    ["SAC interest in month 180", ["financing", "sac", "schedule", 179, "interest"]],
    ["PRICE amortization in month 1", ["financing", "price", "schedule", 0, "amortization"]],
  ])("resolves the metric '%s' to its path", (label, path) => {
    expect(fullmatch(METRIC_PATTERN, label)).toBe(true);
    expect(parseMetric(label).path).toEqual(path);
  });

  it("rejects an unknown metric, in the pattern and in the parser", () => {
    expect(fullmatch(METRIC_PATTERN, "monthly rent")).toBe(false);
    expect(() => parseMetric("monthly rent")).toThrow(UnknownMetricError);
    expect(() => parseMetric("toString")).toThrow(UnknownMetricError); // not a Python case: an inherited name
  });

  it("reads a nested value", () => {
    const result = { financing: { sac: { schedule: [{ interest: 1.5 }] } } };
    expect(parseMetric("SAC interest in month 1").read(result)).toBe(1.5);
  });
});
