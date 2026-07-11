"""Typed shapes for the CRM account data tool."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


ContractStatus = Literal["Active", "Expiring", "Churned", "Pending"]
CrmErrorCode = Literal["account_not_found", "crm_unavailable"]


class AccountHealthSignals(TypedDict):
    days_to_renewal: int
    renewal_within_60_days: bool
    has_recent_crm_note: bool
    contract_at_risk: bool


class CrmAccountData(TypedDict):
    account_id: str
    account_name: str
    account_owner: str
    renewal_date: str
    contract_status: ContractStatus
    plan_tier: str
    customer_status: str
    account_notes: str
    last_task_date: str | None
    health_signals: AccountHealthSignals


class CrmToolSuccess(TypedDict):
    ok: Literal[True]
    data: CrmAccountData


class CrmToolError(TypedDict):
    ok: Literal[False]
    error: CrmErrorCode
    account_id: str
    message: str


CrmToolResult = CrmToolSuccess | CrmToolError


class MockAccountRecord(TypedDict):
    account_id: str
    account_name: str
    account_owner: str
    renewal_date: str
    contract_status: ContractStatus
    plan_tier: str
    account_notes: str
    customer_status: NotRequired[str]
    last_task_date: NotRequired[str | None]
