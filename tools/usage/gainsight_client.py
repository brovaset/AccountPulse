"""Read-only Gainsight (NXT) client for AccountPulse product-usage signals."""

from __future__ import annotations

import json
import os
from typing import Any

from tools._http import HttpClientError, request_json

DEFAULT_COMPANY_ID_MAP = {
    "acc_001": "acc_001",
    "333055649511": "acc_001",
    "acc_002": "acc_002",
    "332906103502": "acc_002",
    "acc_003": "acc_003",
    "333057467115": "acc_003",
}


class GainsightClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def gainsight_enabled() -> bool:
    provider = os.getenv("USAGE_PROVIDER", "auto").strip().lower()
    has_creds = bool(
        os.getenv("GAINSIGHT_ACCESS_KEY", "").strip()
        and os.getenv("GAINSIGHT_BASE_URL", "").strip()
    )
    if provider == "mock":
        return False
    if provider == "gainsight":
        return True
    return has_creds


def _company_id_map() -> dict[str, str]:
    raw = os.getenv("GAINSIGHT_COMPANY_ID_MAP", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_COMPANY_ID_MAP)


def _field(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _base_url() -> str:
    base = os.getenv("GAINSIGHT_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise GainsightClientError(
            "usage_service_unavailable",
            "GAINSIGHT_BASE_URL is required",
        )
    return base


def _access_key() -> str:
    key = os.getenv("GAINSIGHT_ACCESS_KEY", "").strip()
    if not key:
        raise GainsightClientError(
            "usage_service_unavailable",
            "GAINSIGHT_ACCESS_KEY is required",
        )
    return key


def _query_company(lookup_value: str) -> dict[str, Any]:
    """Query Gainsight Company object by configurable key field."""

    key_field = _field("GAINSIGHT_COMPANY_KEY_FIELD", "Name")
    login_field = _field("GAINSIGHT_FIELD_LOGINS", "ActiveUsers")
    decline_field = _field("GAINSIGHT_FIELD_USAGE_DECLINE", "UsageDeclinePercent")
    adoption_field = _field("GAINSIGHT_FIELD_ADOPTION", "FeatureAdoptionPercent")
    last_active_field = _field("GAINSIGHT_FIELD_LAST_ACTIVE", "LastActiveDate")
    trend_field = _field("GAINSIGHT_FIELD_USAGE_TREND", "UsageTrend")

    select = list(
        {
            "Name",
            "GSID",
            key_field,
            login_field,
            decline_field,
            adoption_field,
            last_active_field,
            trend_field,
        }
    )
    body = {
        "select": select,
        "where": {
            "conditions": [
                {
                    "name": key_field,
                    "alias": "A",
                    "value": [lookup_value],
                    "operator": "EQ",
                }
            ],
            "expression": "A",
        },
        "limit": 1,
    }
    url = f"{_base_url()}/v1/data/objects/query/Company"
    try:
        payload = request_json(
            "POST",
            url,
            headers={
                "Accesskey": _access_key(),
                "Content-Type": "application/json",
            },
            body=body,
        )
    except HttpClientError as exc:
        code = (
            "account_not_found"
            if exc.code == "account_not_found"
            else "usage_service_unavailable"
        )
        raise GainsightClientError(code, exc.message) from exc

    records = (
        (payload.get("data") or {}).get("records")
        or payload.get("records")
        or []
    )
    if not records:
        raise GainsightClientError(
            "account_not_found",
            f"No Gainsight Company for {key_field}={lookup_value}",
        )
    return records[0]


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fetch_gainsight_usage_account(account_id: str) -> dict[str, Any]:
    """Fetch product-usage signals from Gainsight Company fields."""

    lookup = _company_id_map().get(account_id, account_id)
    record = _query_company(lookup)

    login_field = _field("GAINSIGHT_FIELD_LOGINS", "ActiveUsers")
    decline_field = _field("GAINSIGHT_FIELD_USAGE_DECLINE", "UsageDeclinePercent")
    adoption_field = _field("GAINSIGHT_FIELD_ADOPTION", "FeatureAdoptionPercent")
    last_active_field = _field("GAINSIGHT_FIELD_LAST_ACTIVE", "LastActiveDate")
    trend_field = _field("GAINSIGHT_FIELD_USAGE_TREND", "UsageTrend")

    decline = _as_float(record.get(decline_field), 0.0)
    trend = str(record.get(trend_field) or "").strip().lower()
    if not trend:
        if decline >= 20:
            trend = "declining"
        elif decline > 0:
            trend = "stable"
        else:
            trend = "stable"

    last_active = record.get(last_active_field)
    if isinstance(last_active, str):
        last_active_date = last_active[:10]
    else:
        last_active_date = None

    return {
        "account_id": account_id,
        "last_active_date": last_active_date,
        "login_frequency_30d": _as_int(record.get(login_field), 0),
        "usage_trend": trend,
        "feature_adoption_percent": _as_int(record.get(adoption_field), 0),
        "usage_decline_percent": int(round(decline)),
        "usage_dropped_over_20_percent": decline >= 20,
        "data_source": "gainsight",
        "gainsight_lookup": lookup,
        "gainsight_gsid": record.get("GSID"),
    }
