"""Read-only CRM account data tool (HubSpot + mock fallback)."""

from __future__ import annotations

import os
from datetime import date, datetime

from tools.crm.hubspot_client import (
    HubSpotClientError,
    fetch_hubspot_account,
    hubspot_enabled,
)
from tools.crm.mock_data import MOCK_ACCOUNTS
from tools.crm.models import (
    AccountHealthSignals,
    CrmAccountData,
    CrmErrorCode,
    CrmToolError,
    CrmToolResult,
    MockAccountRecord,
)

AT_RISK_STATUSES = frozenset({"Expiring", "Churned", "Pending"})


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _build_health_signals(
    record: MockAccountRecord,
    *,
    as_of: date,
) -> AccountHealthSignals:
    renewal_date = _parse_iso_date(record["renewal_date"])
    days_to_renewal = (renewal_date - as_of).days
    notes = (record.get("account_notes") or "").strip()

    return {
        "days_to_renewal": days_to_renewal,
        "renewal_within_60_days": 0 <= days_to_renewal <= 60,
        "has_recent_crm_note": bool(notes),
        "contract_at_risk": record["contract_status"] in AT_RISK_STATUSES,
    }


def _success(data: CrmAccountData) -> CrmToolResult:
    return {"ok": True, "data": data}


def _error(
    account_id: str,
    code: CrmErrorCode,
    message: str,
) -> CrmToolError:
    return {
        "ok": False,
        "error": code,
        "account_id": account_id,
        "message": message,
    }


def _load_mock_record(account_id: str) -> MockAccountRecord | None:
    return MOCK_ACCOUNTS.get(account_id)


def get_crm_account_data(
    account_id: str,
    *,
    as_of: date | None = None,
    force_error: bool | None = None,
) -> CrmToolResult:
    """Fetch CRM account fields and basic health signals.

    Uses HubSpot when ``HUBSPOT_ACCESS_TOKEN`` is set (or ``CRM_PROVIDER=hubspot``).
    Otherwise falls back to local mock fixtures.
    Set CRM_FORCE_ERROR=1 (or pass force_error=True) to simulate outages.
    """
    account_id = (account_id or "").strip()
    if not account_id:
        return _error("", "account_not_found", "account_id is required")

    simulate_outage = (
        force_error
        if force_error is not None
        else os.getenv("CRM_FORCE_ERROR", "").strip() in {"1", "true", "TRUE", "yes"}
    )
    if simulate_outage:
        return _error(
            account_id,
            "crm_unavailable",
            "CRM API is temporarily unavailable",
        )

    try:
        if hubspot_enabled():
            record = fetch_hubspot_account(account_id)
        else:
            record = _load_mock_record(account_id)
            if record is None:
                return _error(
                    account_id,
                    "account_not_found",
                    f"No CRM account found for id '{account_id}'",
                )
    except HubSpotClientError as exc:
        code: CrmErrorCode = (
            "account_not_found"
            if exc.code == "account_not_found"
            else "crm_unavailable"
        )
        return _error(account_id, code, exc.message)

    reference_date = as_of or date.today()
    health_signals = _build_health_signals(record, as_of=reference_date)

    data: CrmAccountData = {
        "account_id": record["account_id"],
        "account_name": record["account_name"],
        "account_owner": record["account_owner"],
        "renewal_date": record["renewal_date"],
        "contract_status": record["contract_status"],
        "plan_tier": record["plan_tier"],
        "account_notes": record.get("account_notes") or "",
        "last_task_date": record.get("last_task_date"),
        "health_signals": health_signals,
    }
    return _success(data)
