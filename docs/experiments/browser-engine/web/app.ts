/**
 * Proof-of-concept UI: the MVP's main path (docs/plan/mvp.md) computed entirely in the browser.
 * Pick a preset or type the contract, see the real cost, the credit gap and the cash ladder.
 * `?engine=ts|pyodide|brython` picks the engine; nothing is sent to a server.
 *
 * `window.sincero` is the hook harness/ uses to measure, diff and run behave through the page.
 */
import { FIELDS } from "../../../../engine/src/index.js";
import { ENGINES, Engine, EngineName, Kind, Reply } from "./engines.js";

// ----- engine + harness hook ------------------------------------------------------------------------
const params = new URLSearchParams(location.search);
const engineName = (params.get("engine") ?? "ts") as EngineName;
if (!(engineName in ENGINES)) throw new Error(`unknown engine: ${engineName}`);
const engine: Engine = ENGINES[engineName]();

interface Hook {
  engine: EngineName;
  state: "loading" | "ready" | "error";
  error?: string;
  timings: { ready?: number; firstResult?: number; lastCompute?: number };
  /** The TypeScript port's field table (harness/differential.py checks it against the Python DTOs). */
  fields: typeof FIELDS;
  callJson(kind: Kind, requestJson: string): string;
  bench(kind: Kind, requestJson: string, n: number): number;
}
declare global {
  interface Window {
    sincero: Hook;
  }
}
window.sincero = {
  engine: engineName,
  state: "loading",
  timings: {},
  fields: FIELDS,
  callJson: (kind, json) => engine.callJson(kind, json),
  bench(kind, json, n) {
    const t0 = performance.now();
    for (let i = 0; i < n; i++) JSON.parse(engine.callJson(kind, json)); // what the UI pays: call + parse
    return (performance.now() - t0) / n;
  },
};

function call<T>(kind: Kind, request: object): Reply & { value?: T } {
  return JSON.parse(engine.callJson(kind, JSON.stringify(request)));
}

// ----- formatting -----------------------------------------------------------------------------------
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const money = (x: number) => brl.format(x);
const num = (x: number) => x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); // table cells: R$ in the header
const pct = (x: number) => `${x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

// ----- the form -------------------------------------------------------------------------------------
const DEFAULTS = Object.fromEntries(FIELDS.map((f) => [f.name, f.default]));
// cli_controller.REFERENCE_PROPERTIES, with the CLI's R$ 13,000 of FGTS
const PRESETS: Record<string, [number, number]> = {
  SO: [300_000, 4], F: [396_000, 8], SV: [233_000, 17], F4: [320_400, 19], RA: [440_000, 19],
};

interface FieldUi {
  name: string;
  label: string;
  hint?: string;
  optional?: string; // placeholder when blank = null / none
  more?: boolean;
}
const FORM: FieldUi[] = [
  { name: "list_price", label: "List price (R$)" },
  { name: "months_remaining", label: "Months remaining until delivery", hint: "time left, not the project's total duration" },
  { name: "down_payment_pct", label: "Down payment (% of the price)" },
  { name: "fgts_upfront", label: "FGTS at signing (R$)" },
  { name: "cash_upfront", label: "Cash at signing (R$)" },
  { name: "pre_approved_credit", label: "Credit pre-approved by the bank (R$)", optional: "blank: the financed balance" },
  { name: "developer_installment", label: "Monthly installment to the developer (R$)", optional: "blank: balance ÷ months", more: true },
  { name: "balloon_months", label: "Months with a balloon payment", optional: "e.g. 6, 12 — the amount is derived", more: true },
  { name: "incc_rate_pa", label: "INCC (% per year)", more: true },
  { name: "bank_rate_pa", label: "Bank interest rate (% per year)", more: true },
  { name: "term_months", label: "Financing term (months)", more: true },
  { name: "itbi_pct", label: "ITBI (% of the price)", more: true },
  { name: "registry_pct", label: "Registry and deed (% of the price)", more: true },
  { name: "income_commitment_ratio", label: "Max share of income for the installment (0–1)", more: true },
  { name: "pro_soluto_months", label: "Months to pay a credit gap (pro-soluto)", more: true },
];

function fieldHtml(f: FieldUi): string {
  const value = f.optional ? "" : String(DEFAULTS[f.name] ?? "");
  const type = f.name === "balloon_months" ? "text" : "number";
  return `<label class="field"><span>${esc(f.label)}</span>
    <input id="f-${f.name}" name="${f.name}" type="${type}" step="any" value="${esc(value)}"
           placeholder="${esc(f.optional ?? "")}" inputmode="decimal">
    ${f.hint ? `<small>${esc(f.hint)}</small>` : ""}</label>`;
}

function buildForm(): void {
  $("presets").innerHTML = Object.keys(PRESETS)
    .map((p) => `<button type="button" class="preset" data-preset="${p}">${p}</button>`)
    .join("");
  $("main-fields").innerHTML = FORM.filter((f) => !f.more).map(fieldHtml).join("");
  $("more-fields").innerHTML = FORM.filter((f) => f.more).map(fieldHtml).join("");
  loadPreset("RA");
}

function loadPreset(name: string): void {
  const [price, months] = PRESETS[name];
  $<HTMLInputElement>("f-list_price").value = String(price);
  $<HTMLInputElement>("f-months_remaining").value = String(months);
  $<HTMLInputElement>("f-fgts_upfront").value = "13000";
  $<HTMLInputElement>("f-name").value = name;
  document.querySelectorAll(".preset").forEach((b) => b.classList.toggle("active", (b as HTMLElement).dataset.preset === name));
}

function readInput(): Record<string, unknown> {
  const data: Record<string, unknown> = { name: $<HTMLInputElement>("f-name").value.trim() || "CUSTOM" };
  for (const f of FORM) {
    const raw = $<HTMLInputElement>(`f-${f.name}`).value.trim();
    if (f.name === "balloon_months") {
      data.balloon_months = raw ? raw.split(/[\s,;]+/).filter(Boolean).map(Number) : [];
    } else if (raw === "") {
      if (f.optional) data[f.name] = null; // null: "let the model derive it"
    } else {
      data[f.name] = Number(raw);
    }
  }
  return data;
}

const ladderAmounts = (): number[] =>
  $<HTMLInputElement>("ladder").value.split(/[\s,;]+/).filter(Boolean).map(Number).filter((x) => Number.isFinite(x));

// ----- results --------------------------------------------------------------------------------------
type Dict = Record<string, any>; // the JSON payload of app/views/json_view.py

function render(): void {
  const input = readInput();
  const t0 = performance.now();
  const sim = call<Dict>("simulate", { input });
  const ladder = sim.ok ? call<Dict>("cash_ladder", { input, amounts: ladderAmounts() }) : undefined;
  const elapsed = performance.now() - t0;
  window.sincero.timings.lastCompute = elapsed;
  $("compute").textContent = `${elapsed.toFixed(1)} ms`;

  if (!sim.ok) {
    $("error").hidden = false;
    $("error").textContent = sim.error;
    $("results").classList.add("stale");
    return;
  }
  $("error").hidden = true;
  $("results").classList.remove("stale");
  const r = sim.value!;
  const tc = r.total_cost;
  const gap = r.credit_gap;

  $("headline").innerHTML = `
    <div class="big">${money(tc.additional)} <span>(${pct(tc.extra_pct)})</span></div>
    <div>on top of the list price of ${money(tc.list_price)}, before the first bank installment:
      <strong>${money(tc.total)}</strong> in total.</div>`;

  $("breakdown").innerHTML = `<table><thead><tr><th>R$</th><th>Base</th><th>Added</th><th>Final</th></tr></thead><tbody>
    ${tc.breakdown
      .map((l: Dict) => `<tr class="${l.component === "Total" ? "total" : ""}"><td>${esc(l.component)}</td>
        <td>${num(l.base_value)}</td><td>${num(l.additional)}</td><td>${num(l.final_value)}</td></tr>`)
      .join("")}</tbody></table>`;

  $("gap").innerHTML =
    gap.gap > 0.005
      ? `<div class="big warn">${money(gap.gap)}</div>
         <div>The bank pre-approved ${money(gap.pre_approved)}, but the balance at delivery is
         ${money(gap.needed)} after INCC. Without more credit you pay the developer
         <strong>${money(gap.pro_soluto_installment)} × ${gap.pro_soluto_months}</strong> (pro-soluto).</div>`
      : `<div class="big ok">No gap</div><div>The pre-approved ${money(gap.pre_approved)} covers the
         ${money(gap.needed)} due at delivery.</div>`;

  const sac = r.financing.sac;
  const price = r.financing.price;
  $("financing").innerHTML = `<table><tbody>
    <tr><td>SAC first / last installment</td><td>${money(sac.first_installment)} → ${money(sac.last_installment)}</td></tr>
    <tr><td>PRICE installment</td><td>${money(price.installment)}</td></tr>
    <tr><td>Minimum income (SAC)</td><td>${money(sac.min_income)}</td></tr>
    <tr><td>Peak month before delivery</td><td>month ${r.timeline.peak_month}: ${money(r.timeline.peak_total)}</td></tr>
  </tbody></table>`;

  if (ladder?.ok) {
    const rows = ladder.value!.scenarios as Dict[];
    const closes = rows.findIndex((s) => s.summary.credit_gap <= 0.005);
    $("ladder-table").innerHTML = `<table><thead><tr><th>Cash at signing (R$)</th><th>Extra cost</th><th>Credit gap</th>
      <th>SAC 1st installment</th></tr></thead><tbody>${rows
        .map((s, i) => `<tr class="${i === closes ? "closes" : ""}"><td>${num(s.overrides.cash_upfront)}</td>
          <td>${num(s.summary.total_cost - s.summary.list_price)} <span class="pct">(${pct(s.summary.extra_pct)})</span></td>
          <td>${num(s.summary.credit_gap)}${i === closes ? ' <span class="pct">✓ closes the gap</span>' : ""}</td>
          <td>${num(s.summary.sac_first_installment)}</td></tr>`)
        .join("")}</tbody></table>`;
  } else {
    $("ladder-table").innerHTML = `<p class="muted">${esc(ladder?.ok === false ? ladder.error : "")}</p>`;
  }

  $("chart").innerHTML = chart(r.timeline.months.slice(0, r.input.months_remaining + 1));
}

const SERIES: [key: string, label: string, color: string][] = [
  ["upfront", "Upfront", "#8d99ae"],
  ["developer_installment", "Developer installment", "#2b6cb0"],
  ["balloon", "Balloon", "#dd6b20"],
  ["construction_interest", "Construction interest", "#c53030"],
];

/** Stacked bars of the construction phase (months 0..N): what leaves the buyer's pocket each month. */
function chart(months: Dict[]): string {
  const w = 640, h = 220, pad = 36;
  const max = Math.max(...months.map((m) => m.total), 1);
  const bw = (w - pad) / months.length;
  const bars = months
    .map((m, i) => {
      let y = h - 20;
      return SERIES.map(([key, label, color]) => {
        const bh = ((h - 44) * m[key]) / max; // 24 px of headroom for the scale label
        y -= bh;
        return bh > 0 ? `<rect x="${pad + i * bw + 1}" y="${y}" width="${Math.max(bw - 2, 1)}" height="${bh}" fill="${color}"><title>month ${m.month} — ${label}: ${money(m[key])}</title></rect>` : "";
      }).join("");
    })
    .join("");
  const ticks = months
    .filter((_, i) => months.length <= 24 || i % Math.ceil(months.length / 12) === 0)
    .map((m) => `<text x="${pad + m.month * bw + bw / 2}" y="${h - 5}" text-anchor="middle">${m.month}</text>`)
    .join("");
  const legend = SERIES.map(([, label, color]) => `<span><i style="background:${color}"></i>${label}</span>`).join("");
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Monthly payments until delivery">
      <text x="0" y="12">${money(max)}</text>${bars}${ticks}</svg><div class="legend">${legend}</div>`;
}

// ----- wiring ---------------------------------------------------------------------------------------
let timer: number | undefined;
const schedule = () => {
  clearTimeout(timer);
  timer = window.setTimeout(render, 120);
};

async function main(): Promise<void> {
  document.querySelectorAll<HTMLAnchorElement>("#engines a").forEach((a) => a.classList.toggle("active", a.dataset.engine === engineName));
  $("engine-label").textContent = engine.label;
  buildForm();
  $("presets").addEventListener("click", (e) => {
    const p = (e.target as HTMLElement).dataset.preset;
    if (p) {
      loadPreset(p);
      schedule();
    }
  });
  $("form").addEventListener("input", schedule);
  $("ladder").addEventListener("input", schedule);

  try {
    await engine.load();
  } catch (exc) {
    window.sincero.state = "error";
    window.sincero.error = String(exc);
    $("loading").textContent = `The engine failed to load: ${exc}`;
    return;
  }
  window.sincero.timings.ready = performance.now();
  $("loaded").textContent = `${(window.sincero.timings.ready / 1000).toFixed(1)} s`;
  $("loading").hidden = true;
  $("app").hidden = false;
  render();
  window.sincero.timings.firstResult = performance.now();
  window.sincero.state = "ready";
}

main();
