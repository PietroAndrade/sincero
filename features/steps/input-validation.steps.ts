/** features/steps/input_validation_steps.py */
import assert from "node:assert/strict";
import { Then } from "@cucumber/cucumber";
import type { SimulationWorld } from "../support/world.js";

Then("the simulation should be rejected with the error {string}", function (this: SimulationWorld, message: string) {
  assert.ok(this.error !== null, "the simulation was expected to be rejected but it succeeded");
  assert.equal(this.error, message, `rejection message: expected '${message}', observed '${this.error}'`);
});
