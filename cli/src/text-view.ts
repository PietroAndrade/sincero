/**
 * The plain-text report for the terminal (app/views/text_view.py), character for character:
 * the CLI's fixtures hold what the Python CLI printed, and the tests compare.
 */
import { formatAmount, monthTotal } from "@sincero/engine";
import type { SimulationResult, WhatIfPayload } from "@sincero/engine";

/** R$ 1.234,56 (Python's `f"{value:,.2f}"` with the separators swapped). */
export function brl(value: number): string {
  return "R$ " + formatAmount(value).replace(/[,.]/g, (c) => (c === "," ? "." : ","));
}

/** `f"{x:.2f}"`: formatAmount without its thousands separators (the same rounding). */
const fixed2 = (x: number) => formatAmount(x).replace(/,/g, "");

const left = (s: string | number, width: number) => String(s).padEnd(width);
const right = (s: string | number, width: number) => String(s).padStart(width);

export function report(r: SimulationResult): string {
  const { contract: inp } = r.input;
  const { downPayment: dp, constructionInterest: ci, creditGap: cg, timeline: tl } = r;
  const rule = "=".repeat(72);
  const lines = [
    rule,
    `🏠 ${inp.name}  |  ${brl(inp.list_price)}  |  ${inp.months_remaining} months remaining`,
    rule,
    `${left("Component", 24)}${right("Base", 15)}${right("Additional", 16)}${right("Final", 17)}`,
  ];
  for (const line of [...r.totalCost.lines, r.totalCost.totalLine])
    lines.push(
      `${left(line.component, 24)}${right(brl(line.base_value), 15)}${right(brl(line.additional), 16)}` +
        `${right(brl(line.base_value + line.additional), 17)}`,
    );
  const first = dp.schedule[0]!;
  const last = dp.schedule.at(-1)!;
  lines.push(
    `Extra cost over list price: ${fixed2(r.totalCost.extraPct)}%`,
    "",
    `Developer: ${brl(dp.nominalInstallment)}/month nominal  ` +
      `(month 1: ${brl(first.installment)}, last: ${brl(last.installment)})` +
      (dp.balloons.length
        ? `  +  ${dp.balloons.length} balloon(s) of ${brl(dp.nominalBalloon)} nominal in months ` +
          dp.balloons.map((b) => String(b.month)).join(", ")
        : ""),
    `Construction interest: month 1 ${brl(ci.schedule[0]!.interest)} → last ${brl(ci.schedule.at(-1)!.interest)}` +
      `  |  total ${brl(ci.total)}`,
    `SAC:   1st ${brl(r.sac.firstInstallment)}  last ${brl(r.sac.lastInstallment)}  min income ${brl(r.sac.minIncome)}`,
    `PRICE: fixed ${brl(r.price.installment)}  min income ${brl(r.price.minIncome)}`,
    `Credit gap at delivery: ${brl(cg.gap)} (pre-approved ${brl(cg.preApproved)} vs needed ${brl(cg.needed)})` +
      ` → pro-soluto ${brl(cg.proSolutoInstallment)} x ${cg.proSolutoMonths}`,
    `Peak month: ${tl.peak.month} (${brl(monthTotal(tl.peak))})  |  construction phase total ${brl(tl.constructionPhaseTotal)}`,
  );
  return lines.join("\n");
}

export function comparisonTable(results: readonly SimulationResult[]): string {
  const header =
    `${left("Name", 5)}${right("Price", 14)}${right("Left", 5)}${right("Dev/mo", 13)}${right("Hidden INCC", 14)}` +
    `${right("Balance@deliv", 16)}${right("Constr.int", 13)}${right("SAC 1st", 12)}${right("Min income", 14)}`;
  const rows = results.map((r) => {
    const c = r.input.contract;
    return (
      `${left(c.name, 5)}${right(brl(c.list_price), 14)}${right(c.months_remaining, 5)}` +
      `${right(brl(r.downPayment.nominalInstallment), 13)}${right(brl(r.mortgage.hiddenInccDebt), 14)}` +
      `${right(brl(r.mortgage.corrected), 16)}${right(brl(r.constructionInterest.total), 13)}` +
      `${right(brl(r.sac.firstInstallment), 12)}${right(brl(r.sac.minIncome), 14)}`
    );
  });
  return [header, ...rows].join("\n");
}

/** The cash ladder's table (cli_controller.run_cash_ladder). */
export function ladderTable(ladder: WhatIfPayload): string {
  const header =
    `${right("Cash upfront", 14)}${right("Dev/mo", 13)}${right("Hidden INCC", 14)}${right("Balance@deliv", 16)}` +
    `${right("SAC 1st", 12)}${right("Min income", 14)}`;
  const rows = ladder.scenarios.map(({ summary: s }) => {
    const m = (key: string) => brl(s[key] as number);
    return (
      `${right(m("cash_upfront"), 14)}${right(m("developer_installment"), 13)}${right(m("hidden_incc_debt"), 14)}` +
      `${right(m("balance_at_delivery"), 16)}${right(m("sac_first_installment"), 12)}${right(m("min_income_sac"), 14)}`
    );
  });
  return [header, ...rows].join("\n");
}
