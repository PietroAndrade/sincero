"""Unit tests for the behave support library (no behave, no engine run needed)."""
import re

import pytest

from support.metrics import METRIC_PATTERN, STATIC_METRICS, parse_metric
from support.money import MONEY_PATTERN, PERCENT_PATTERN, describe_mismatch, is_close, parse_money, parse_percent


@pytest.mark.parametrize("text,value", [
    ("R$ 1,234.56", 1234.56), ("1,234.56", 1234.56), ("0.00", 0.0), ("-3.10", -3.10), ("440,000.00", 440000.0),
])
def test_parse_money(text, value):
    assert parse_money(text) == value


def test_parse_money_rejects_garbage():
    with pytest.raises(ValueError):
        parse_money("R$ ")


@pytest.mark.parametrize("text,value", [("20.0%", 20.0), ("18.613", 18.613), ("0", 0.0)])
def test_parse_percent(text, value):
    assert parse_percent(text) == value


def test_money_pattern_matches_what_features_write():
    for sample in ("88,000.00", "0.00", "152.26", "1,234,567.89"):
        assert re.fullmatch(MONEY_PATTERN, sample), sample
    assert re.fullmatch(PERCENT_PATTERN, "18.613")


def test_is_close_uses_half_a_cent():
    assert is_close(100.004, 100.0)
    assert not is_close(100.006, 100.0)


def test_describe_mismatch_names_expected_and_observed():
    assert describe_mismatch("credit gap", 10.0, 12.5) == "credit gap: expected 10.00, observed 12.50 (diff +2.50)"


def test_every_static_metric_is_matched_by_the_pattern():
    for label in STATIC_METRICS:
        assert re.fullmatch(METRIC_PATTERN, label), label


@pytest.mark.parametrize("label,path", [
    ("credit gap", ("credit_gap", "gap")),
    ("developer installment in month 3", ("down_payment", "schedule", 2, "installment")),
    ("SAC interest in month 180", ("financing", "sac", "schedule", 179, "interest")),
    ("PRICE amortization in month 1", ("financing", "price", "schedule", 0, "amortization")),
])
def test_parse_metric_resolves_paths(label, path):
    assert re.fullmatch(METRIC_PATTERN, label)
    assert parse_metric(label).path == path


def test_unknown_metric_is_rejected_by_pattern_and_parser():
    assert not re.fullmatch(METRIC_PATTERN, "monthly rent")
    with pytest.raises(KeyError):
        parse_metric("monthly rent")


def test_metric_reads_nested_value():
    result = {"financing": {"sac": {"schedule": [{"interest": 1.5}]}}}
    assert parse_metric("SAC interest in month 1").read(result) == 1.5
