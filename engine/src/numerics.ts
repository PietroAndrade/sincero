/**
 * The arithmetic the engine needs beyond `+ - * / **`. These functions were ported so the engine
 * reproduces the retired Python engine to the last bit (the golden master checks that), and each
 * one is also sound on its own terms:
 *
 *   compensatedSum(xs)   Neumaier compensated summation, which is what CPython >= 3.12 `sum()` does for
 *                        floats. A naive `a + b + …` gives 0.9999999999999999 for ten 0.1s; this
 *                        gives 1.0. Every schedule total goes through it, so do not replace it with a
 *                        loop: the golden master fails on 2,254 figures if you do.
 *   formatAmount(x)      `1,234.57`: two decimals, comma thousands, exact ties rounded to even
 *                        (CPython's `f"{x:,.2f}"`). `toFixed` rounds ties up instead. It is used in the
 *                        model's error messages, which the scenarios compare verbatim.
 *   firstMaxBy, maxOf    `max()` as the model uses it: on equal keys the FIRST item wins.
 */

/** The sum of `xs`, with compensation for the low bits each addition loses. */
export function compensatedSum(xs: Iterable<number>): number {
  let hi = 0.0;
  let lo = 0.0;
  for (const x of xs) {
    const t = hi + x;
    if (Math.abs(hi) >= Math.abs(x)) lo += hi - t + x;
    else lo += x - t + hi;
    hi = t;
  }
  // As CPython does: do not lose the sign of a negative result, and do not turn an infinite or
  // overflowed sum into NaN by adding the compensation.
  return lo !== 0 && Number.isFinite(lo) ? hi + lo : hi;
}

/** The FIRST item with the largest key. */
export function firstMaxBy<T>(items: readonly T[], key: (item: T) => number): T {
  if (items.length === 0) throw new Error("firstMaxBy() of an empty sequence");
  let best = items[0] as T;
  let bestKey = key(best);
  for (let i = 1; i < items.length; i++) {
    const item = items[i] as T;
    const k = key(item);
    if (k > bestKey) {
      best = item;
      bestKey = k;
    }
  }
  return best;
}

/** The larger of two numbers: `a` unless `b` is strictly larger (the first of equals wins). */
export function maxOf(a: number, b: number): number {
  return b > a ? b : a;
}

/** `x` with two decimals and comma thousands separators, exact ties rounded to the even cent. */
export function formatAmount(x: number): string {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  const negative = x < 0 || Object.is(x, -0);
  const a = Math.abs(x);
  let fixed: string;
  const eighths = a * 8; // exact: a power-of-two scaling
  if (Number.isInteger(eighths) && eighths % 2 === 1) {
    // a = n/8 with n odd: a × 100 = 12.5 n ends in exactly .5, a tie. Round it to the even cent.
    // In integers, because a × 100 is not exact in doubles from 2^49 up (every double from 2^50 up
    // is a multiple of 1/4, so no tie exists there).
    const floorCents = (BigInt(eighths) * 25n) / 2n; // ⌊12.5 n⌋
    const even = floorCents % 2n === 0n ? floorCents : floorCents + 1n;
    fixed = `${even / 100n}.${String(even % 100n).padStart(2, "0")}`;
  } else if (a >= 1e21) {
    fixed = `${BigInt(a)}.00`; // toFixed switches to exponent notation here
  } else {
    fixed = a.toFixed(2); // the exact decimal expansion of the double, rounded: right off ties
  }
  const [int = "", frac = ""] = fixed.split(".");
  return `${negative ? "-" : ""}${int.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${frac}`;
}
