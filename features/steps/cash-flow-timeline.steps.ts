/** features/steps/cash_flow_timeline_steps.py */
import assert from "node:assert/strict";
import { Then } from "@cucumber/cucumber";
import type { DataTable } from "@cucumber/cucumber";
import { describeMismatch, isClose, parseMoney } from "../support/money.js";
import type { SimulationWorld } from "../support/world.js";

type Month = Record<string, number>;
const timeline = (world: SimulationWorld) =>
  world.current().timeline as { months: Month[]; peak_month: number; peak_total: number; construction_phase_total: number };

Then("the timeline should have {int} months", function (this: SimulationWorld, count: number) {
  const actual = timeline(this).months.length;
  assert.equal(actual, count, `timeline length: expected ${count} months, observed ${actual}`);
});

Then("the timeline in month {int} should be:", function (this: SimulationWorld, month: number, table: DataTable) {
  const row = timeline(this).months[month]!;
  assert.equal(row.month, month, `timeline row ${month} is labelled month ${row.month}`);
  const rows = table.hashes();
  assert.equal(rows.length, 1, `the table of month ${month} has ${rows.length} rows, expected one`);
  for (const [column, text] of Object.entries(rows[0]!)) {
    const expected = parseMoney(text);
    assert.ok(isClose(row[column]!, expected), describeMismatch(`month ${month}.${column}`, expected, row[column]!));
  }
});

Then("the peak monthly outflow should be R$ {money} in month {int}", function (this: SimulationWorld, amount: number, month: number) {
  const t = timeline(this);
  assert.equal(t.peak_month, month, `peak month: expected ${month}, observed ${t.peak_month}`);
  assert.ok(isClose(t.peak_total, amount), describeMismatch("peak total", amount, t.peak_total));
});

Then("the total outflow during the construction phase should be R$ {money}", function (this: SimulationWorld, amount: number) {
  const actual = timeline(this).construction_phase_total;
  assert.ok(isClose(actual, amount), describeMismatch("construction phase total", amount, actual));
});
