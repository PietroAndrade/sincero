/**
 * What behave's features/environment.py did: the custom parameter types of the step patterns, and
 * the world. Loaded before the step definitions (cucumber.mjs imports support/ first).
 *
 *   {money}    R$ figures as the features write them: 440,000.00 / -3.10    -> number
 *   {percent}  a percentage without its sign: 7.0 / 18.613                 -> number
 *   {metric}   a registered business phrase ("credit gap", "SAC interest in month 3") -> Metric
 */
import { defineParameterType, setWorldConstructor } from "@cucumber/cucumber";
import { METRIC_PATTERN, parseMetric } from "./metrics.js";
import { MONEY_PATTERN, PERCENT_PATTERN, parseMoney, parsePercent } from "./money.js";
import { SimulationWorld } from "./world.js";

defineParameterType({ name: "money", regexp: MONEY_PATTERN, transformer: parseMoney, useForSnippets: false });
defineParameterType({ name: "percent", regexp: PERCENT_PATTERN, transformer: parsePercent, useForSnippets: false });
defineParameterType({ name: "metric", regexp: METRIC_PATTERN, transformer: parseMetric, useForSnippets: false });

setWorldConstructor(SimulationWorld);
