/** `assert actual == pytest.approx(expected)`: within 1e-6 of `expected`, relatively (or 1e-12 absolutely). */
import { expect } from "vitest";

export function expectApprox(actual: number, expected: number, rel = 1e-6, abs = 1e-12): void {
  const tolerance = Math.max(rel * Math.abs(expected), abs);
  expect(Math.abs(actual - expected), `${actual} ≈ ${expected} ± ${tolerance}`).toBeLessThanOrEqual(tolerance);
}
