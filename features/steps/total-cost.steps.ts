/** features/steps/total_cost_steps.py */
import assert from "node:assert/strict";
import { Then } from "@cucumber/cucumber";
import type { DataTable } from "@cucumber/cucumber";
import { describeMismatch, isClose, parseMoney } from "../support/money.js";
import type { SimulationWorld } from "../support/world.js";

const COLUMNS = ["base_value", "additional", "final_value"] as const;
type Line = { component: string } & Record<(typeof COLUMNS)[number], number>;

Then("the cost breakdown should be:", function (this: SimulationWorld, table: DataTable) {
  const breakdown = (this.current().total_cost as { breakdown: Line[] }).breakdown;
  const observed = new Map(breakdown.map((line) => [line.component, line]));
  const expectedComponents = table.hashes().map((row) => row.component!);
  assert.deepEqual(
    [...observed.keys()],
    expectedComponents,
    `breakdown rows: expected ${JSON.stringify(expectedComponents)}, observed ${JSON.stringify([...observed.keys()])}`,
  );
  for (const row of table.hashes()) {
    for (const column of COLUMNS) {
      const expected = parseMoney(row[column]!);
      const actual = observed.get(row.component!)![column];
      assert.ok(isClose(actual, expected), describeMismatch(`${row.component}.${column}`, expected, actual));
    }
  }
});

Then("the total extra cost over the list price should be {percent}%", function (this: SimulationWorld, percent: number) {
  const actual = (this.current().total_cost as { extra_pct: number }).extra_pct;
  assert.ok(isClose(actual, percent), `extra cost: expected ${percent.toFixed(2)}%, observed ${actual.toFixed(2)}%`);
});
