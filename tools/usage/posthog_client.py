"""Read-only PostHog client for AccountPulse product-usage signals."""

from __future__ import annotations

import json
import os
from typing import Any

from tools._http import HttpClientError, request_json

DEFAULT_ACCOUNT_MAP = {
    "acc_001": "acc_001",
    "333055649511": "acc_001",
    "acc_002": "acc_002",
    "332906103502": "acc_002",
    "acc_003": "acc_003",
    "333057467115": "acc_003",
}


class PostHogClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def posthog_enabled() -> bool:
    provider = os.getenv("USAGE_PROVIDER", "auto").strip().lower()
    has_creds = bool(
        os.getenv("POSTHOG_PERSONAL_API_KEY", "").strip()
        and os.getenv("POSTHOG_PROJECT_ID", "").strip()
    )
    if provider == "mock":
        return False
    if provider == "posthog":
        return True
    if provider in {"gainsight"}:
        return False
    return has_creds


def _account_map() -> dict[str, str]:
    raw = os.getenv("POSTHOG_ACCOUNT_MAP", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_ACCOUNT_MAP)


def _host() -> str:
    return (
        os.getenv("POSTHOG_HOST", "https://us.posthog.com").strip().rstrip("/")
        or "https://us.posthog.com"
    )


def _project_id() -> str:
    project_id = os.getenv("POSTHOG_PROJECT_ID", "").strip()
    if not project_id:
        raise PostHogClientError(
            "usage_service_unavailable",
            "POSTHOG_PROJECT_ID is required",
        )
    return project_id


def _api_key() -> str:
    key = os.getenv("POSTHOG_PERSONAL_API_KEY", "").strip()
    if not key:
        raise PostHogClientError(
            "usage_service_unavailable",
            "POSTHOG_PERSONAL_API_KEY is required",
        )
    return key


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _hogql(query: str) -> dict[str, Any]:
    url = f"{_host()}/api/projects/{_project_id()}/query/"
    try:
        return request_json(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            body={
                "query": {"kind": "HogQLQuery", "query": query},
                "name": "accountpulse_usage",
            },
        )
    except HttpClientError as exc:
        code = (
            "account_not_found"
            if exc.code == "account_not_found"
            else "usage_service_unavailable"
        )
        raise PostHogClientError(code, exc.message) from exc


def _first_row(payload: dict[str, Any]) -> list[Any] | None:
    results = payload.get("results") or []
    if not results:
        return None
    row = results[0]
    return row if isinstance(row, list) else [row]


def _account_filter(account_key: str) -> str:
    """Build HogQL predicate for one account."""

    template = os.getenv(
        "POSTHOG_FILTER_TEMPLATE",
        "toString(properties.account_id) = '{account}'",
    )
    return template.format(account=_escape(account_key))


def fetch_posthog_usage_account(account_id: str) -> dict[str, Any]:
    """Fetch usage signals from PostHog event counts for an account."""

    account_key = _account_map().get(account_id, account_id)
    event = os.getenv("POSTHOG_EVENT", "$pageview").strip() or "$pageview"
    event_sql = _escape(event)
    filt = _account_filter(account_key)

    current_q = f"""
SELECT
  count() AS event_count,
  count(DISTINCT distinct_id) AS users,
  count(DISTINCT event) AS distinct_events,
  max(timestamp) AS last_seen
FROM events
WHERE event = '{event_sql}'
  AND ({filt})
  AND timestamp >= now() - INTERVAL 30 DAY
""".strip()

    previous_q = f"""
SELECT count() AS event_count
FROM events
WHERE event = '{event_sql}'
  AND ({filt})
  AND timestamp >= now() - INTERVAL 60 DAY
  AND timestamp < now() - INTERVAL 30 DAY
""".strip()

    current = _first_row(_hogql(current_q))
    previous = _first_row(_hogql(previous_q))

    current_count = int(current[0] or 0) if current else 0
    users = int(current[1] or 0) if current and len(current) > 1 else 0
    distinct_events = int(current[2] or 0) if current and len(current) > 2 else 0
    last_seen = current[3] if current and len(current) > 3 else None
    previous_count = int(previous[0] or 0) if previous else 0

    if current_count == 0 and previous_count == 0 and users == 0:
        raise PostHogClientError(
            "account_not_found",
            f"No PostHog events for account_id={account_id} "
            f"(filter key={account_key})",
        )

    if previous_count > 0:
        decline = max(
            0.0,
            ((previous_count - current_count) / previous_count) * 100.0,
        )
    else:
        decline = 0.0

    if current_count == 0:
        trend = "inactive"
    elif decline >= 20:
        trend = "declining"
    else:
        trend = "stable"

    if isinstance(last_seen, str):
        last_active_date = last_seen[:10]
    else:
        last_active_date = None

    # Rough adoption proxy: unique event names in window, capped at 100.
    adoption = min(100, distinct_events * 12) if distinct_events else 0

    return {
        "account_id": account_id,
        "last_active_date": last_active_date,
        "login_frequency_30d": current_count,
        "usage_trend": trend,
        "feature_adoption_percent": adoption,
        "usage_decline_percent": int(round(decline)),
        "usage_dropped_over_20_percent": decline >= 20,
        "data_source": "posthog",
        "posthog_account_key": account_key,
        "posthog_users_30d": users,
        "posthog_previous_30d_events": previous_count,
    }
