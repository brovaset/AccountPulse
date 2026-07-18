"""Display date helpers for AccountPulse reports and UI.

Machine payloads keep ISO ``YYYY-MM-DD``. Human-facing text uses
``Mon DD, YYYY`` (e.g. ``Aug 25, 2026``).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def parse_iso_date(value: Any) -> date | None:
    """Parse ISO date/datetime strings (and ``date`` / ``datetime`` values)."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # Accept full ISO timestamps by taking the date portion.
    text = text.replace("Z", "+00:00")
    try:
        if "T" in text:
            return datetime.fromisoformat(text).date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def format_display_date(
    value: Any,
    *,
    fallback: str = "—",
) -> str:
    """Format a date for CSM-facing reports and UI.

    Returns ``fallback`` when the value is missing or not a parseable date.
    Already-display-formatted strings are returned unchanged when parse fails.
    """

    parsed = parse_iso_date(value)
    if parsed is None:
        if value is None or str(value).strip() == "":
            return fallback
        return str(value).strip()
    return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"
