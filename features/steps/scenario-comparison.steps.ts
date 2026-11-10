/** features/steps/scenario_comparison_steps.py */
import assert from "node:assert/strict";
import { Given, Then, When } from "@cucumber/cucumber";
import type { DataTable } from "@cucumber/cucumber";
import { describeMismatch, isClose, parseMoney } from "../support/money.js";
import type { SimulationWorld } from "../support/world.js";

Given("the candidate properties:", function (this: SimulationWorld, table: DataTable) {
  this.setCandidates(
    table.hashes().map((row) => ({ name: row.name, list_price: parseMoney(row.price!), months_remaining: Number.parseInt(row.months!, 10) })),
  );
});

When("the buyer compares the candidate properties", function (this: SimulationWorld) {
  this.compareCandidates();
});

When("the buyer compares paying the following cash upfront:", function (this: SimulationWorld, table: DataTable) {
  this.compareCash(table.hashes().map((row) => parseMoney(row.cash!)));
});

When("the buyer re-runs the simulation with the INCC at {percent}% per year", function (this: SimulationWorld, rate: number) {
  this.rerun({ incc_rate_pa: rate });
});

When("the buyer re-runs the simulation with R$ {money} in cash upfront", function (this: SimulationWorld, amount: number) {
  this.rerun({ cash_upfront: amount });
});

/** Every expected column but `key`, to the half cent, row by row. */
function assertTableMatches(expectedRows: Record<string, string>[], observedRows: Record<string, unknown>[], key: string): void {
  assert.equal(expectedRows.length, observedRows.length, `rows: expected ${expectedRows.length}, observed ${observedRows.length}`);
  expectedRows.forEach((expected, i) => {
    const observed = observedRows[i]!;
    for (const [column, text] of Object.entries(expected)) {
      if (column === key) continue;
      const want = parseMoney(text);
      const got = observed[column] as number;
      assert.ok(isClose(got, want), describeMismatch(`${expected[key]}.${column}`, want, got));
    }
  });
}

Then("the comparison table should be:", function (this: SimulationWorld, table: DataTable) {
  assert.ok(this.comparison !== null, "the properties were never compared");
  const names = table.hashes().map((row) => row.name);
  const observed = this.comparison.map((row) => row.name);
  assert.deepEqual(observed, names, `comparison order: expected ${JSON.stringify(names)}, observed ${JSON.stringify(observed)}`);
  assertTableMatches(table.hashes(), this.comparison, "name");
});

Then("the cash ladder should be:", function (this: SimulationWorld, table: DataTable) {
  assert.ok(this.cashLadder !== null, "the cash amounts were never compared");
  const amounts = table.hashes().map((row) => parseMoney(row.cash!));
  const observed = this.cashLadder.map((row) => row.cash);
  assert.deepEqual(observed, amounts, `cash ladder: expected ${JSON.stringify(amounts)}, observed ${JSON.stringify(observed)}`);
  assertTableMatches(table.hashes(), this.cashLadder, "cash");
});
