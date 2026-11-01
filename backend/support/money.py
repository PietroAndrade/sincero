"""Parsing and comparing money/percentage figures written in business language."""
from __future__ import annotations

import re

HALF_CENT = 0.005

# Patterns used by the behave `parse` types (no capturing groups allowed).
MONEY_PATTERN = r"-?[\d,]+(?:\.\d+)?"
PERCENT_PATTERN = r"-?\d+(?:\.\d+)?"


def parse_money(text: str) -> float:
    """'R$ 1,234.56' / '1,234.56' / '-3.10' -> 1234.56"""
    cleaned = re.sub(r"[^\d.\-]", "", text)
    if cleaned in ("", "-", "."):
        raise ValueError(f"not a money figure: {text!r}")
    return float(cleaned)


def parse_percent(text: str) -> float:
    """'20.0%' / '20.0' -> 20.0"""
    return float(text.replace("%", "").strip())


def is_close(actual: float, expected: float, tolerance: float = HALF_CENT) -> bool:
    return abs(actual - expected) <= tolerance


def describe_mismatch(label: str, expected: float, actual: float) -> str:
    return f"{label}: expected {expected:,.2f}, observed {actual:,.2f} (diff {actual - expected:+,.2f})"
