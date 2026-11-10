/** Parsing and comparing money and percentage figures written in business language (support/money.py). */

export const HALF_CENT = 0.005;

// The patterns of the {money} and {percent} parameter types (no capturing groups: cucumber would
// pass each group to the transformer as an argument).
export const MONEY_PATTERN = /-?[\d,]+(?:\.\d+)?/;
export const PERCENT_PATTERN = /-?\d+(?:\.\d+)?/;

/** 'R$ 1,234.56' / '1,234.56' / '-3.10' -> 1234.56 */
export function parseMoney(text: string): number {
  const cleaned = text.replace(/[^\d.\-]/g, "");
  const value = Number(cleaned);
  if (cleaned === "" || cleaned === "-" || cleaned === "." || Number.isNaN(value))
    throw new RangeError(`not a money figure: '${text}'`);
  return value;
}

/** '20.0%' / '20.0' -> 20.0 */
export function parsePercent(text: string): number {
  const cleaned = text.replace("%", "").trim();
  const value = Number(cleaned);
  if (cleaned === "" || Number.isNaN(value)) throw new RangeError(`not a percentage: '${text}'`);
  return value;
}

export function isClose(actual: number, expected: number, tolerance = HALF_CENT): boolean {
  return Math.abs(actual - expected) <= tolerance;
}

const twoDecimals = (x: number, sign: "auto" | "always" = "auto") =>
  x.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: sign });

export function describeMismatch(label: string, expected: number, actual: number): string {
  return `${label}: expected ${twoDecimals(expected)}, observed ${twoDecimals(actual)} (diff ${twoDecimals(actual - expected, "always")})`;
}

/** `{:,.2f}` for the assertion messages. */
export const money = (x: number): string => twoDecimals(x);
