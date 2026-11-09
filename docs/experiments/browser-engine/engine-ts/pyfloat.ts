/**
 * The two places where JavaScript and CPython disagree about the same floats, reproduced so that
 * the port gives the Python engine's figures to the last bit, not just to the cent.
 *
 *   pySum(xs)        CPython >= 3.12 `sum()` of floats: Neumaier compensated summation, not `a + b + …`.
 *                    A naive loop gives 0.9999999999999999 for ten 0.1s; CPython gives 1.0.
 *   pyMoney(x)       CPython `f"{x:,.2f}"`: round-half-even on exact ties (0.125 -> "0.12");
 *                    `toFixed` rounds them up ("0.13"). Used in the model's error messages.
 */

/** `sum(xs)` as CPython 3.12+ computes it for floats (Python/bltinmodule.c, `cs_add` / `cs_to_double`). */
export function pySum(xs: Iterable<number>): number {
  let hi = 0.0;
  let lo = 0.0;
  for (const x of xs) {
    const t = hi + x;
    if (Math.abs(hi) >= Math.abs(x)) lo += (hi - t) + x;
    else lo += (x - t) + hi;
    hi = t;
  }
  // "Avoid losing the sign on a negative result, and don't let adding the compensation convert an
  // infinite or overflowed sum to a NaN."
  return lo !== 0 && Number.isFinite(lo) ? hi + lo : hi;
}

/** `max(items, key=key)`: the FIRST item with the largest key, as Python does. */
export function pyMaxBy<T>(items: readonly T[], key: (item: T) => number): T {
  if (items.length === 0) throw new Error("max() arg is an empty sequence");
  let best = items[0];
  let bestKey = key(best);
  for (let i = 1; i < items.length; i++) {
    const k = key(items[i]);
    if (k > bestKey) {
      best = items[i];
      bestKey = k;
    }
  }
  return best;
}

/** `max(a, b)` for two floats: `a` unless `b` is strictly larger (Python keeps the first of equals). */
export function pyMax(a: number, b: number): number {
  return b > a ? b : a;
}

/** `f"{x:,.2f}"`. */
export function pyMoney(x: number): string {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  const negative = x < 0 || Object.is(x, -0);
  const a = Math.abs(x);
  let fixed: string;
  const eighths = a * 8; // exact: a power-of-two scaling
  if (a < 2 ** 49 && Number.isInteger(eighths) && eighths % 2 === 1) {
    // a = n/8 with n odd: a × 100 ends in exactly .5, a tie. Python rounds it to the even cent.
    const cents = Math.floor(a * 100); // a × 100 = 12.5 n is exact here
    const even = BigInt(cents % 2 === 0 ? cents : cents + 1);
    fixed = `${even / 100n}.${String(even % 100n).padStart(2, "0")}`;
  } else if (a >= 1e21) {
    fixed = `${BigInt(a)}.00`; // toFixed switches to exponent notation here; Python does not
  } else {
    fixed = a.toFixed(2); // exact decimal expansion of the double, rounded: matches Python off ties
  }
  const [int, frac] = fixed.split(".");
  return `${negative ? "-" : ""}${int.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${frac}`;
}
