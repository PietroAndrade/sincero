/**
 * The translation table between the business wording of the feature files and where the figure
 * lives in a simulation payload (support/metrics.py).
 *
 * Static metrics map a phrase to a path. Dynamic metrics ("SAC installment in month 3") are
 * recognised by a regex and resolved into a path when parsed. METRIC_PATTERN is the alternation the
 * {metric} parameter type matches, so a generic "the {metric} should be R$ ..." step only ever
 * matches a registered phrase.
 */
export type Path = readonly (string | number)[];

export const STATIC_METRICS: Readonly<Record<string, Path>> = {
  "required down payment": ["down_payment", "required"],
  "down payment balance to be paid during construction": ["down_payment", "remaining"],
  "nominal monthly developer installment": ["down_payment", "nominal_installment"],
  "amount not covered by the monthly installments": ["down_payment", "missing_amount"],
  "nominal balloon payment": ["down_payment", "nominal_balloon"],
  "total paid to the developer during construction": ["down_payment", "total_paid"],
  "INCC correction on the down payment": ["down_payment", "incc_correction"],
  "nominal mortgage balance": ["mortgage", "nominal_balance"],
  "mortgage balance at delivery": ["mortgage", "corrected_balance"],
  "hidden INCC debt on the mortgage balance": ["mortgage", "hidden_incc_debt"],
  "total construction interest": ["construction_interest", "total"],
  ITBI: ["closing_costs", "itbi"],
  "registry and deed costs": ["closing_costs", "registry"],
  "SAC monthly amortization": ["financing", "sac", "amortization"],
  "PRICE installment": ["financing", "price", "installment"],
  "total interest paid under SAC": ["financing", "sac", "total_interest"],
  "total interest paid under PRICE": ["financing", "price", "total_interest"],
  "minimum income for SAC": ["financing", "sac", "min_income"],
  "minimum income for PRICE": ["financing", "price", "min_income"],
  "credit needed at delivery": ["credit_gap", "needed"],
  "credit gap": ["credit_gap", "gap"],
  "pro-soluto monthly installment": ["credit_gap", "pro_soluto_installment"],
};

// (regex, path builder): month numbers in the wording are 1-based, schedules are lists.
const DYNAMIC_METRICS: readonly [RegExp, (m: RegExpMatchArray) => Path][] = [
  [/^developer installment in month (\d+)$/, (m) => ["down_payment", "schedule", Number(m[1]) - 1, "installment"]],
  [/^balloon payment in month (\d+)$/, (m) => ["down_payment", "schedule", Number(m[1]) - 1, "balloon"]],
  [/^construction interest in month (\d+)$/, (m) => ["construction_interest", "schedule", Number(m[1]) - 1, "interest"]],
  [
    /^(SAC|PRICE) (installment|interest|amortization) in month (\d+)$/,
    (m) => ["financing", m[1]!.toLowerCase(), "schedule", Number(m[3]) - 1, m[2]!],
  ],
];

const DYNAMIC_PATTERNS = [
  String.raw`developer installment in month \d+`,
  String.raw`balloon payment in month \d+`,
  String.raw`construction interest in month \d+`,
  String.raw`(?:SAC|PRICE) (?:installment|interest|amortization) in month \d+`,
];

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Longest phrases first, so that a phrase is never matched by one of its prefixes. */
export const METRIC_PATTERN = new RegExp(
  [...Object.keys(STATIC_METRICS).sort((a, b) => b.length - a.length).map(escapeRegExp), ...DYNAMIC_PATTERNS].join("|"),
);

export class Metric {
  constructor(
    readonly label: string,
    readonly path: Path,
  ) {}

  read(result: unknown): number {
    let node: unknown = result;
    for (const key of this.path) {
      if (node === null || typeof node !== "object" || !(key in node))
        throw new TypeError(`${this.label}: no ${JSON.stringify(key)} at ${JSON.stringify(this.path)}`);
      node = (node as Record<string | number, unknown>)[key];
    }
    if (typeof node !== "number") throw new TypeError(`${this.label}: ${JSON.stringify(this.path)} is not a number`);
    return node;
  }
}

export class UnknownMetricError extends Error {
  override name = "UnknownMetricError";
}

export function parseMetric(text: string): Metric {
  const label = text.trim();
  const path = STATIC_METRICS[label];
  if (path !== undefined && Object.hasOwn(STATIC_METRICS, label)) return new Metric(label, path);
  for (const [pattern, build] of DYNAMIC_METRICS) {
    const match = label.match(pattern);
    if (match) return new Metric(label, build(match));
  }
  throw new UnknownMetricError(`no metric registered for '${label}'`);
}
