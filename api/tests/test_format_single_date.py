"""Tests for format_single_date + style= extension of format_date_range.

Mirrors the TypeScript `formatSingleDate` helper in
web/src/lib/sections/DateField.tsx and the shared `DATE_STYLE_OPTIONS` list.
"""
import pytest

from app.services.renderer.builders._utils import (
    DATE_STYLE_OPTIONS,
    format_date_range,
    format_single_date,
)


PRESETS = [
    ("YYYY-MM", "YYYY-MM (default)", " – ", "2021-03"),
    ("YYYY/MM", "YYYY/MM", "/", "2021/03"),
    ("MM/YYYY", "MM/YYYY", "/", "03/2021"),
    ("MM-YYYY", "MM-YYYY", "-", "03-2021"),
    ("MM.YYYY", "MM.YYYY", ".", "03.2021"),
    ("YYYY.MM", "YYYY.MM", ".", "2021.03"),
    ("Mon YYYY", "Mon YYYY", " – ", "Mar 2021"),
    ("Month YYYY", "Month YYYY", " – ", "March 2021"),
    ("YYYY", "YYYY", " – ", "2021"),
    ("Mon-YYYY", "Mon-YYYY", "-", "Mar-2021"),
]

def test_date_style_options_count():
    assert len(DATE_STYLE_OPTIONS) == 10

def test_date_style_options_keys_match_presets():
    keys = [p[0] for p in PRESETS]
    assert [k for k, _l, _s in DATE_STYLE_OPTIONS] == keys


@pytest.mark.parametrize("key,_label,range_sep,expected", PRESETS)
def test_format_single_date_for_each_preset(key, _label, range_sep, expected):
    style = {"key": key, "range_sep": range_sep}
    assert format_single_date("2021-03", style) == expected


@pytest.mark.parametrize("key,_label,range_sep,expected", PRESETS)
def test_format_single_date_january_key_edge(key, _label, range_sep, expected):
    style = {"key": key, "range_sep": range_sep}
    # January is the first month — checks 0-index vs 1-index off-by-one
    out = format_single_date("2021-01", style)
    if key == "YYYY-MM":
        assert out == "2021-01"
    elif key == "YYYY/MM":
        assert out == "2021/01"
    elif key == "MM/YYYY":
        assert out == "01/2021"
    elif key == "MM-YYYY":
        assert out == "01-2021"
    elif key == "MM.YYYY":
        assert out == "01.2021"
    elif key == "YYYY.MM":
        assert out == "2021.01"
    elif key == "Mon YYYY":
        assert out == "Jan 2021"
    elif key == "Month YYYY":
        assert out == "January 2021"
    elif key == "YYYY":
        assert out == "2021"
    elif key == "Mon-YYYY":
        assert out == "Jan-2021"


def test_format_single_date_empty_returns_empty():
    for style in [
        None,
        {},
        {"key": "Mon YYYY", "range_sep": "\u2013 "},
    ]:
        assert format_single_date("", style) == ""


def test_format_single_date_none_returns_empty():
    for style in [None, {"key": "Mon YYYY", "range_sep": "\u2013 "}]:
        assert format_single_date(None, style) == ""


def test_format_single_date_legacy_year_only_returns_raw():
    style = {"key": "Mon YYYY", "range_sep": " \u2013 "}
    # "2020" doesn't have a month — fall back to raw value
    assert format_single_date("2020", style) == "2020"


def test_format_single_date_out_of_range_month_returns_raw():
    style = {"key": "Mon YYYY", "range_sep": " \u2013 "}
    assert format_single_date("2021-13", style) == "2021-13"


def test_format_single_date_no_style_returns_raw():
    assert format_single_date("2021-03") == "2021-03"
    assert format_single_date("2021-03", None) == "2021-03"


def test_format_single_date_empty_style_key_returns_raw():
    assert format_single_date("2021-03", {"key": "", "range_sep": "x"}) == "2021-03"


def test_format_single_date_unknown_key_returns_raw():
    assert format_single_date("2021-03", {"key": "Garbage", "range_sep": "x"}) == "2021-03"


# --- format_date_range with style= ------------------------------------


def test_format_date_range_with_style_default_unchanged():
    # No style → identical to legacy behavior
    assert format_date_range("2021-03", "2022-01", False) == "2021-03 \u2013 2022-01"


def test_format_date_range_with_style_reformats_both_bounds():
    style = {"key": "Month YYYY", "range_sep": " \u2013 "}
    out = format_date_range("2021-03", "2022-01", False, style)
    assert out == "March 2021 \u2013 January 2022"


def test_format_date_range_with_style_current_uses_present():
    style = {"key": "Month YYYY", "range_sep": " \u2013 "}
    out = format_date_range("2021-03", "2022-01", True, style)
    # `current` wins regardless of style; start is formatted
    assert out == "March 2021 \u2013 Present"


def test_format_date_range_with_style_empty_end_returns_styled_start():
    style = {"key": "MM/YYYY", "range_sep": "/"}
    out = format_date_range("2021-03", None, False, style)
    assert out == "03/2021"


def test_format_date_range_with_style_empty_start_returns_empty():
    style = {"key": "Mon YYYY", "range_sep": " \u2013 "}
    assert format_date_range("", None, False, style) == ""


def test_format_date_range_with_style_uses_separator():
    style = {"key": "MM.YYYY", "range_sep": "."}
    out = format_date_range("2021-03", "2022-01", False, style)
    assert out == "03.2021.01.2022"
