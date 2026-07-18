"""Tests for CSM-facing date formatting."""

from datetime import date, datetime

from tools.dates import format_dates_in_text, format_display_date, parse_iso_date


def test_format_display_date_from_iso():
    assert format_display_date("2026-08-25") == "Aug 25, 2026"
    assert format_display_date("2026-08-05") == "Aug 5, 2026"


def test_format_dates_in_text_rewrites_iso_tokens():
    text = "Human approval required before 2026-08-25."
    assert format_dates_in_text(text) == (
        "Human approval required before Aug 25, 2026."
    )


def test_format_display_date_from_date_objects():
    assert format_display_date(date(2026, 8, 25)) == "Aug 25, 2026"
    assert format_display_date(datetime(2026, 8, 25, 12, 0, 0)) == "Aug 25, 2026"


def test_format_display_date_fallback():
    assert format_display_date(None) == "—"
    assert format_display_date("", fallback="renewal") == "renewal"
    assert format_display_date(None, fallback="the renewal date") == (
        "the renewal date"
    )


def test_parse_iso_date_timestamp():
    assert parse_iso_date("2026-08-25T15:30:00Z") == date(2026, 8, 25)
