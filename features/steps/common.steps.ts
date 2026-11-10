/**
 * Shared vocabulary (features/steps/common_steps.py): the Givens that describe the market and the
 * contract, the single When, and the generic money assertions. Feature-specific steps live in
 * their own file.
 */
import assert from "node:assert/strict";
import { Given, Then, When } from "@cucumber/cucumber";
import type { Metric } from "../support/metrics.js";
import { describeMismatch, isClose, money } from "../support/money.js";
import type { SimulationWorld } from "../support/world.js";

// ----- Given: market -------------------------------------------------------------------------------
Given(
  "INCC at {percent}% per year and bank financing at {percent}% per year over {int} months",
  function (this: SimulationWorld, incc: number, bank: number, term: number) {
    this.setMarket(incc, bank, term);
  },
);

Given("the bank accepts installments up to {percent}% of the household income", function (this: SimulationWorld, ratio: number) {
  this.set({ income_commitment_ratio: ratio / 100.0 });
});

Given(
  "closing costs of ITBI {percent}% and registry {percent}% of the list price",
  function (this: SimulationWorld, itbi: number, registry: number) {
    this.set({ itbi_pct: itbi, registry_pct: registry });
  },
);

// ----- Given: property and contract -----------------------------------------------------------------
Given(
  "a property {string} listed at R$ {money} with {int} months remaining until delivery",
  function (this: SimulationWorld, name: string, price: number, months: number) {
    this.setProperty(name, price, months);
  },
);

Given("the developer requires a down payment of {percent}% of the list price", function (this: SimulationWorld, percent: number) {
  this.set({ down_payment_pct: percent });
});

Given("the buyer pays R$ {money} of FGTS upfront", function (this: SimulationWorld, amount: number) {
  this.set({ fgts_upfront: amount });
});

Given("the buyer pays R$ {money} in cash upfront", function (this: SimulationWorld, amount: number) {
  this.set({ cash_upfront: amount });
});

Given("the buyer pays the developer R$ {money} per month", function (this: SimulationWorld, amount: number) {
  this.set({ developer_installment: amount });
});

Given("the contract has a balloon payment in month {int}", function (this: SimulationWorld, month: number) {
  this.set({ balloon_months: [month] });
});

Given("the contract has balloon payments in months {int} and {int}", function (this: SimulationWorld, first: number, second: number) {
  this.set({ balloon_months: [first, second] });
});

Given("the bank pre-approved a credit of R$ {money}", function (this: SimulationWorld, amount: number) {
  this.set({ pre_approved_credit: amount });
});

Given("any pro-soluto debt is paid to the developer over {int} months", function (this: SimulationWorld, months: number) {
  this.set({ pro_soluto_months: months });
});

// ----- When ----------------------------------------------------------------------------------------
When("the buyer runs the simulation", function (this: SimulationWorld) {
  this.run();
});

// ----- Then: generic money figures -------------------------------------------------------------------
Then("the {metric} should be R$ {money}", function (this: SimulationWorld, metric: Metric, expected: number) {
  const actual = this.metric(metric);
  assert.ok(isClose(actual, expected), describeMismatch(metric.label, expected, actual));
});

Then(
  "the {metric} should drop from R$ {money} to R$ {money}",
  function (this: SimulationWorld, metric: Metric, before: number, after: number) {
    const was = this.previousMetric(metric);
    const now = this.metric(metric);
    assert.ok(isClose(was, before), describeMismatch(`${metric.label} (before)`, before, was));
    assert.ok(isClose(now, after), describeMismatch(`${metric.label} (after)`, after, now));
    assert.ok(now < was, `${metric.label} did not drop: ${money(was)} -> ${money(now)}`);
  },
);
