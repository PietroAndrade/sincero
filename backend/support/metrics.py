"""
Translation table between the business wording used in the feature files and the
location of the figure inside a simulation result.

Static metrics map a phrase to a path; dynamic metrics ("SAC installment in month 3")
are recognised by a regex and resolved into a path at parse time. `METRIC_PATTERN`
is the alternation behave's `parse` matcher uses, so a generic
"the {metric} should be R$ ..." step only ever matches a registered phrase.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

Path = tuple[Any, ...]

STATIC_METRICS: dict[str, Path] = {
    "required down payment": ("down_payment", "required"),
    "down payment balance to be paid during construction": ("down_payment", "remaining"),
    "nominal monthly developer installment": ("down_payment", "nominal_installment"),
    "amount not covered by the monthly installments": ("down_payment", "missing_amount"),
    "nominal balloon payment": ("down_payment", "nominal_balloon"),
    "total paid to the developer during construction": ("down_payment", "total_paid"),
    "INCC correction on the down payment": ("down_payment", "incc_correction"),
    "nominal mortgage balance": ("mortgage", "nominal_balance"),
    "mortgage balance at delivery": ("mortgage", "corrected_balance"),
    "hidden INCC debt on the mortgage balance": ("mortgage", "hidden_incc_debt"),
    "total construction interest": ("construction_interest", "total"),
    "ITBI": ("closing_costs", "itbi"),
    "registry and deed costs": ("closing_costs", "registry"),
    "SAC monthly amortization": ("financing", "sac", "amortization"),
    "PRICE installment": ("financing", "price", "installment"),
    "total interest paid under SAC": ("financing", "sac", "total_interest"),
    "total interest paid under PRICE": ("financing", "price", "total_interest"),
    "minimum income for SAC": ("financing", "sac", "min_income"),
    "minimum income for PRICE": ("financing", "price", "min_income"),
    "credit needed at delivery": ("credit_gap", "needed"),
    "credit gap": ("credit_gap", "gap"),
    "pro-soluto monthly installment": ("credit_gap", "pro_soluto_installment"),
}

# (regex, path builder) — month numbers in the wording are 1-based, schedules are lists.
DYNAMIC_METRICS: list[tuple[re.Pattern, Callable[[re.Match], Path]]] = [
    (re.compile(r"^developer installment in month (\d+)$"),
     lambda m: ("down_payment", "schedule", int(m[1]) - 1, "installment")),
    (re.compile(r"^balloon payment in month (\d+)$"),
     lambda m: ("down_payment", "schedule", int(m[1]) - 1, "balloon")),
    (re.compile(r"^construction interest in month (\d+)$"),
     lambda m: ("construction_interest", "schedule", int(m[1]) - 1, "interest")),
    (re.compile(r"^(SAC|PRICE) (installment|interest|amortization) in month (\d+)$"),
     lambda m: ("financing", m[1].lower(), "schedule", int(m[3]) - 1, m[2])),
]

_DYNAMIC_PATTERNS = [
    r"developer installment in month \d+",
    r"balloon payment in month \d+",
    r"construction interest in month \d+",
    r"(?:SAC|PRICE) (?:installment|interest|amortization) in month \d+",
]

METRIC_PATTERN = "|".join(
    [re.escape(label) for label in sorted(STATIC_METRICS, key=len, reverse=True)] + _DYNAMIC_PATTERNS
)


@dataclass(frozen=True)
class Metric:
    label: str
    path: Path

    def read(self, result: dict) -> float:
        node: Any = result
        for key in self.path:
            node = node[key]
        return float(node)


def parse_metric(label: str) -> Metric:
    label = label.strip()
    if label in STATIC_METRICS:
        return Metric(label, STATIC_METRICS[label])
    for pattern, build in DYNAMIC_METRICS:
        match = pattern.match(label)
        if match:
            return Metric(label, build(match))
    raise KeyError(f"no metric registered for '{label}'")
