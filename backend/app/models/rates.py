"""Interest/index rate conversions."""
from __future__ import annotations

from dataclasses import dataclass


def annual_to_monthly(rate_pa_pct: float) -> float:
    """Convert an annual percentage (e.g. 7.0) to the equivalent compounded monthly rate."""
    return (1.0 + rate_pa_pct / 100.0) ** (1.0 / 12.0) - 1.0


@dataclass(frozen=True)
class MonthlyRate:
    """A monthly compounded rate derived from an annual percentage."""

    annual_pct: float

    @property
    def monthly(self) -> float:
        return annual_to_monthly(self.annual_pct)

    def factor(self, months: int) -> float:
        """Accumulated growth after `months` months: (1 + i)^months."""
        return (1.0 + self.monthly) ** months
