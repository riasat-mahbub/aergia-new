"""Tests for format_date_range helper (mirrors the TS version)."""
from app.services.renderer.builders._utils import format_date_range


def test_empty_start_returns_empty():
    assert format_date_range("", None, False) == ""
    assert format_date_range("", "", False) == ""
    assert format_date_range("", None, True) == ""


def test_empty_end_current_false_returns_start():
    assert format_date_range("2021-03", None, False) == "2021-03"
    assert format_date_range("2021-03", "", False) == "2021-03"


def test_empty_end_current_true_returns_start_present():
    assert format_date_range("2021-03", None, True) == "2021-03 – Present"
    assert format_date_range("2021-03", "", True) == "2021-03 – Present"


def test_both_set_returns_start_end():
    assert format_date_range("2021-03", "2022-01", False) == "2021-03 – 2022-01"


def test_current_overrides_end_value():
    assert format_date_range("2021-03", "2022-01", True) == "2021-03 – Present"
