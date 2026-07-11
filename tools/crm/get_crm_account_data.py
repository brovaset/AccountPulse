"""Read-only CRM account data tool (mock-backed for MVP)."""

from __future__ import annotations

from json import tool
import os
from datetime import date, datetime
from strands import tool
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

@tool
def get_crm_account_data(
    account_id: str,
    *,
    as_of: date | None = None,
    force_error: bool | None = None,
) -> CrmToolResult:
    """Fetch CRM account fields and basic health signals.

    Read-only. Uses mock fixtures until a real CRM client is wired in.
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

    record = MOCK_ACCOUNTS.get(account_id)
    if record is None:
        return _error(
            account_id,
            "account_not_found",
            f"No CRM account found for id '{account_id}'",
        )

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
