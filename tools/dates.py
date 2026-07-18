"""Display date helpers for AccountPulse reports and UI.

Machine payloads keep ISO ``YYYY-MM-DD``. Human-facing text uses
``Mon D, YYYY`` (e.g. ``Aug 25, 2026``).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


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


def format_dates_in_text(text: str) -> str:
    """Replace ISO ``YYYY-MM-DD`` tokens in prose with display dates.

    Used by the Streamlit UI so cached reports update without a re-run.
    """

    if not text:
        return text

    def _replace(match: re.Match[str]) -> str:
        return format_display_date(match.group(1), fallback=match.group(1))

    return _ISO_DATE_RE.sub(_replace, text)
