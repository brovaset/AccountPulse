"""Read-only HubSpot CRM client for AccountPulse."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Any

from tools.crm.models import ContractStatus, MockAccountRecord

HUBSPOT_API_BASE = "https://api.hubapi.com"


class HubSpotClientError(Exception):
    """Raised when HubSpot cannot fulfill a read request."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def hubspot_enabled() -> bool:
    provider = os.getenv("CRM_PROVIDER", "auto").strip().lower()
    has_token = bool(os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip())
    if provider == "mock":
        return False
    if provider == "hubspot":
        return True
    return has_token


def _token() -> str:
    token = os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip()
    if not token:
        raise HubSpotClientError(
            "crm_unavailable",
            "HUBSPOT_ACCESS_TOKEN is not set",
        )
    return token


def _request(method: str, path: str, *, query: dict[str, str] | None = None) -> Any:
    url = f"{HUBSPOT_API_BASE}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise HubSpotClientError(
                "account_not_found",
                f"HubSpot object not found ({path})",
            ) from exc
        raise HubSpotClientError(
            "crm_unavailable",
            f"HubSpot API error {exc.code}: {detail[:300]}",
        ) from exc
    except urllib.error.URLError as exc:
        raise HubSpotClientError(
            "crm_unavailable",
            f"HubSpot network error: {exc.reason}",
        ) from exc


def _props(*names: str) -> str:
    return ",".join(names)


def _owner_name(owner_id: str | None) -> str:
    if not owner_id:
        return "Unknown"
    try:
        owner = _request("GET", f"/crm/v3/owners/{owner_id}")
    except HubSpotClientError:
        return f"owner:{owner_id}"
    first = (owner.get("firstName") or "").strip()
    last = (owner.get("lastName") or "").strip()
    email = (owner.get("email") or "").strip()
    full = f"{first} {last}".strip()
    return full or email or f"owner:{owner_id}"


def _associated_ids(company_id: str, to_object: str) -> list[str]:
    payload = _request(
        "GET",
        f"/crm/v4/objects/companies/{company_id}/associations/{to_object}",
    )
    results = payload.get("results") or []
    ids: list[str] = []
    for row in results:
        to_id = row.get("toObjectId")
        if to_id is not None:
            ids.append(str(to_id))
    return ids


def _parse_hubspot_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # HubSpot may return YYYY-MM-DD or epoch millis as string.
    if value.isdigit():
        ms = int(value)
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()
    if "T" in value:
        return value.split("T", 1)[0]
    return value[:10]


def _map_contract_status(dealstage: str | None, renewal: str | None) -> ContractStatus:
    stage = (dealstage or "").strip().lower()
    if stage in {"closedlost", "closed_lost"}:
        return "Churned"
    if stage in {"closedwon", "closed_won"}:
        return "Active"
    if renewal:
        try:
            days = (date.fromisoformat(renewal) - date.today()).days
            if 0 <= days <= 60:
                return "Expiring"
        except ValueError:
            pass
    if stage:
        return "Pending"
    return "Active"


def _pick_deal(company_id: str) -> dict[str, Any] | None:
    deal_ids = _associated_ids(company_id, "deals")
    if not deal_ids:
        return None

    best: dict[str, Any] | None = None
    best_date: date | None = None
    today = date.today()

    for deal_id in deal_ids[:10]:
        deal = _request(
            "GET",
            f"/crm/v3/objects/deals/{deal_id}",
            query={
                "properties": _props(
                    "dealname",
                    "dealstage",
                    "closedate",
                    "amount",
                    "pipeline",
                )
            },
        )
        props = deal.get("properties") or {}
        close = _parse_hubspot_date(props.get("closedate"))
        close_date = None
        if close:
            try:
                close_date = date.fromisoformat(close)
            except ValueError:
                close_date = None

        # Prefer the nearest upcoming close date; else the latest known deal.
        score_date = close_date or date.min
        if best is None:
            best, best_date = deal, close_date
            continue
        if close_date and close_date >= today:
            if best_date is None or best_date < today or close_date < best_date:
                best, best_date = deal, close_date
        elif best_date is None or (best_date < today and score_date > best_date):
            best, best_date = deal, close_date

    return best


def _latest_note(company_id: str) -> str:
    note_ids = _associated_ids(company_id, "notes")
    if not note_ids:
        return ""
    # HubSpot returns association order; take the first and enrich if needed.
    latest_body = ""
    latest_ts = ""
    for note_id in note_ids[:5]:
        note = _request(
            "GET",
            f"/crm/v3/objects/notes/{note_id}",
            query={"properties": _props("hs_note_body", "hs_timestamp")},
        )
        props = note.get("properties") or {}
        ts = props.get("hs_timestamp") or ""
        body = (props.get("hs_note_body") or "").strip()
        if not body:
            continue
        if not latest_ts or ts > latest_ts:
            latest_ts = ts
            latest_body = body
    return latest_body


def _latest_task_date(company_id: str) -> str | None:
    task_ids = _associated_ids(company_id, "tasks")
    latest: str | None = None
    for task_id in task_ids[:5]:
        task = _request(
            "GET",
            f"/crm/v3/objects/tasks/{task_id}",
            query={"properties": _props("hs_timestamp", "hs_task_completion_date")},
        )
        props = task.get("properties") or {}
        raw = props.get("hs_task_completion_date") or props.get("hs_timestamp")
        parsed = _parse_hubspot_date(raw)
        if parsed and (latest is None or parsed > latest):
            latest = parsed
    return latest


def fetch_hubspot_account(company_id: str) -> MockAccountRecord:
    """Load a HubSpot company and map it into AccountPulse CRM fields."""
    renewal_prop = os.getenv("HUBSPOT_PROP_RENEWAL", "").strip()
    plan_prop = os.getenv("HUBSPOT_PROP_PLAN_TIER", "").strip() or "type"
    status_prop = os.getenv("HUBSPOT_PROP_CONTRACT_STATUS", "").strip()

    company_props = ["name", "hubspot_owner_id", "lifecyclestage", "description", plan_prop]
    if renewal_prop:
        company_props.append(renewal_prop)
    if status_prop:
        company_props.append(status_prop)

    company = _request(
        "GET",
        f"/crm/v3/objects/companies/{company_id}",
        query={"properties": _props(*dict.fromkeys(company_props))},
    )
    props = company.get("properties") or {}
    deal = _pick_deal(company_id)
    deal_props = (deal or {}).get("properties") or {}

    renewal = None
    if renewal_prop:
        renewal = _parse_hubspot_date(props.get(renewal_prop))
    if not renewal:
        renewal = _parse_hubspot_date(deal_props.get("closedate"))
    if not renewal:
        # Keep schema stable even when HubSpot has no close/renewal date yet.
        renewal = date.today().isoformat()

    if status_prop and props.get(status_prop):
        raw_status = str(props.get(status_prop)).strip().title()
        contract_status: ContractStatus
        if raw_status in {"Active", "Expiring", "Churned", "Pending"}:
            contract_status = raw_status  # type: ignore[assignment]
        else:
            contract_status = _map_contract_status(
                deal_props.get("dealstage"),
                renewal,
            )
    else:
        contract_status = _map_contract_status(deal_props.get("dealstage"), renewal)

    plan_tier = (props.get(plan_prop) or deal_props.get("dealname") or "Unknown").strip()
    notes = _latest_note(company_id) or (props.get("description") or "").strip()

    return {
        "account_id": str(company.get("id") or company_id),
        "account_name": (props.get("name") or f"Company {company_id}").strip(),
        "account_owner": _owner_name(props.get("hubspot_owner_id")),
        "renewal_date": renewal,
        "contract_status": contract_status,
        "plan_tier": plan_tier or "Unknown",
        "account_notes": notes,
        "last_task_date": _latest_task_date(company_id),
    }
