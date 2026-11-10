/**
 * The scenario "world" (support/world.py): collects what the Givens say, performs the When, keeps
 * what the Thens need. Step definitions stay three or four lines because the bookkeeping lives
 * here. cucumber-js builds a new world for every scenario, so each one passes alone and in any order.
 */
import assert from "node:assert/strict";
import { World } from "@cucumber/cucumber";
import type { IWorldOptions } from "@cucumber/cucumber";
import type { FlatInput, Payload, Summary } from "@sincero/engine";
import { EngineGateway } from "./gateway.js";
import type { Gateway } from "./gateway.js";
import { Metric, parseMetric } from "./metrics.js";

export class SimulationWorld extends World {
  engine: Gateway = new EngineGateway();
  market: FlatInput = {};
  contract: FlatInput = {};
  candidates: FlatInput[] = [];
  result: Payload | null = null;
  previousResult: Payload | null = null;
  comparison: Summary[] | null = null;
  cashLadder: (Summary & { cash: number })[] | null = null;
  error: string | null = null;

  constructor(options: IWorldOptions) {
    super(options);
  }

  // ----- givens ----------------------------------------------------------------------------------
  setMarket(incc_rate_pa: number, bank_rate_pa: number, term_months: number): void {
    Object.assign(this.market, { incc_rate_pa, bank_rate_pa, term_months });
  }

  setProperty(name: string, list_price: number, months_remaining: number): void {
    Object.assign(this.contract, { name, list_price, months_remaining });
  }

  /** Any other input field (down_payment_pct, fgts_upfront, …). */
  set(fields: FlatInput): void {
    Object.assign(this.contract, fields);
  }

  setCandidates(rows: readonly FlatInput[]): void {
    this.candidates = [...rows];
  }

  // ----- whens -----------------------------------------------------------------------------------
  inputData(overrides: FlatInput = {}): FlatInput {
    return { ...this.market, ...this.contract, ...overrides };
  }

  run(overrides: FlatInput = {}): void {
    this.error = null;
    this.result = null;
    try {
      this.result = this.engine.simulate(this.inputData(overrides));
    } catch (e) {
      if (!this.engine.isRejection(e)) throw e;
      this.error = e.message;
    }
  }

  rerun(overrides: FlatInput = {}): void {
    this.previousResult = this.result;
    this.run(overrides);
  }

  compareCandidates(): void {
    this.comparison = this.engine.compare(this.candidates.map((c) => this.inputData(c)));
  }

  compareCash(amounts: readonly number[]): void {
    const rows = this.engine.compare(amounts.map((a) => this.inputData({ cash_upfront: a })));
    this.cashLadder = amounts.map((cash, i) => ({ cash, ...rows[i]! }));
  }

  // ----- thens -----------------------------------------------------------------------------------
  current(): Payload {
    assert.equal(this.error, null, `the simulation was rejected: ${this.error}`);
    assert.ok(this.result !== null, "the simulation was never run");
    return this.result;
  }

  previous(): Payload {
    assert.ok(this.previousResult !== null, "there is no previous run to compare with");
    return this.previousResult;
  }

  metric(metric: Metric | string): number {
    return asMetric(metric).read(this.current());
  }

  previousMetric(metric: Metric | string): number {
    return asMetric(metric).read(this.previous());
  }
}

const asMetric = (metric: Metric | string): Metric => (metric instanceof Metric ? metric : parseMetric(metric));
