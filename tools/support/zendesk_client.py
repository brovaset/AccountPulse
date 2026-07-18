"""Read-only Zendesk Support client for AccountPulse."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from tools._http import HttpClientError, basic_auth_header, request_json

# Optional: AccountPulse id / HubSpot company id → Zendesk organization external_id
DEFAULT_EXTERNAL_ID_MAP = {
    "acc_001": "acc_001",
    "333055649511": "acc_001",
    "acc_002": "acc_002",
    "332906103502": "acc_002",
    "acc_003": "acc_003",
    "333057467115": "acc_003",
}


class ZendeskClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def zendesk_enabled() -> bool:
    provider = os.getenv("SUPPORT_PROVIDER", "auto").strip().lower()
    has_creds = bool(
        os.getenv("ZENDESK_SUBDOMAIN", "").strip()
        and os.getenv("ZENDESK_EMAIL", "").strip()
        and os.getenv("ZENDESK_API_TOKEN", "").strip()
    )
    if provider == "mock":
        return False
    if provider == "zendesk":
        return True
    return has_creds


def _json_map(env_name: str, default: dict[str, str] | None = None) -> dict[str, str]:
    raw = os.getenv(env_name, "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    return dict(default or {})


def _external_id_map() -> dict[str, str]:
    mapped = _json_map("ZENDESK_EXTERNAL_ID_MAP")
    return mapped or dict(DEFAULT_EXTERNAL_ID_MAP)


def _org_id_map() -> dict[str, str]:
    """AccountPulse / HubSpot id → Zendesk organization id."""

    return _json_map("ZENDESK_ORG_ID_MAP")


def _resolve_organization_id(account_id: str) -> tuple[Any, str | None]:
    """Return (organization_id, external_id_used_or_None)."""

    org_id = _org_id_map().get(account_id)
    if org_id:
        return org_id, None

    external_id = _external_id_map().get(account_id, account_id)
    org_payload = _request(
        "GET",
        "/organizations/search.json",
        query={"external_id": external_id},
    )
    orgs = org_payload.get("organizations") or []
    if not orgs:
        raise ZendeskClientError(
            "account_not_found",
            f"No Zendesk organization for account_id={account_id} "
            f"(org id map miss; external_id={external_id})",
        )
    return orgs[0].get("id"), external_id


def _auth_header() -> str:
    email = os.getenv("ZENDESK_EMAIL", "").strip()
    token = os.getenv("ZENDESK_API_TOKEN", "").strip()
    if not email or not token:
        raise ZendeskClientError(
            "support_unavailable",
            "ZENDESK_EMAIL and ZENDESK_API_TOKEN are required",
        )
    return basic_auth_header(f"{email}/token", token)


def _base_url() -> str:
    subdomain = os.getenv("ZENDESK_SUBDOMAIN", "").strip()
    if not subdomain:
        raise ZendeskClientError(
            "support_unavailable",
            "ZENDESK_SUBDOMAIN is required",
        )
    return f"https://{subdomain}.zendesk.com/api/v2"


def _request(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
) -> Any:
    try:
        return request_json(
            method,
            f"{_base_url()}{path}",
            headers={"Authorization": _auth_header()},
            query=query,
        )
    except HttpClientError as exc:
        raise ZendeskClientError(exc.code, exc.message) from exc


def _priority_rank(priority: str | None) -> int:
    return {
        "urgent": 4,
        "high": 3,
        "normal": 2,
        "low": 1,
        None: 0,
        "": 0,
    }.get((priority or "").lower(), 0)


def _normalize_severity(priority: str | None) -> str:
    p = (priority or "").lower()
    if p in {"urgent", "high"}:
        return "high"
    if p == "normal":
        return "medium"
    if p == "low":
        return "low"
    return "none"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_zendesk_support_account(account_id: str) -> dict[str, Any]:
    """Fetch open Zendesk tickets for an AccountPulse / HubSpot account id."""

    org_id, external_id = _resolve_organization_id(account_id)
    tickets_payload = _request(
        "GET",
        f"/organizations/{org_id}/tickets.json",
        query={"per_page": "50"},
    )
    tickets = tickets_payload.get("tickets") or []
    open_statuses = {"new", "open", "pending", "hold"}
    open_tickets = [
        t for t in tickets if str(t.get("status") or "").lower() in open_statuses
    ]

    now = datetime.now(timezone.utc)
    ages: list[int] = []
    subjects: list[str] = []
    bodies: list[str] = []
    highest = "none"
    high_over_7 = False
    for ticket in open_tickets:
        created = _parse_dt(ticket.get("created_at"))
        age_days = (now - created).days if created else 0
        ages.append(age_days)
        priority = ticket.get("priority")
        severity = _normalize_severity(priority)
        if _priority_rank(priority) > _priority_rank(
            "high" if highest == "high" else highest
        ):
            highest = severity if severity != "none" else highest
        if severity == "high" and age_days >= 7:
            high_over_7 = True
        tid = ticket.get("id")
        subject = ticket.get("subject") or "Untitled ticket"
        subjects.append(f"TCK-{tid}: {subject}" if tid else subject)
        desc = (ticket.get("description") or "").strip()
        if desc:
            bodies.append(desc[:2000])

    if open_tickets and highest == "none":
        highest = "medium"

    return {
        "account_id": account_id,
        "open_ticket_count": len(open_tickets),
        "oldest_ticket_age_days": max(ages) if ages else 0,
        "highest_severity": highest,
        "unresolved_high_severity_over_7_days": high_over_7,
        "ticket_trend": "stable",
        "recent_ticket_subjects": subjects[:5],
        "recent_ticket_bodies": bodies[:5],
        "data_source": "zendesk",
        "zendesk_organization_id": org_id,
        "zendesk_external_id": external_id,
    }
