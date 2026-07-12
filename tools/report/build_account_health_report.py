"""Build AccountPulse reports from CRM + product-usage tool payloads.

This path does not rely on the LLM to interpret tool JSON, which small local
models often mishandle (e.g. inventing missing account_id failures).
"""

from __future__ import annotations

from typing import Any

from tools.crm import get_crm_account_data
from tools.usage.get_product_usage import fetch_product_usage

RiskLevel = str  # ACTION NEEDED | WATCH | HEALTHY | NEEDS MANUAL REVIEW


def _crm_signals(crm: dict[str, Any]) -> list[str]:
    if not crm.get("ok"):
        return []
    data = crm["data"]
    hs = data.get("health_signals") or {}
    signals: list[str] = []
    if hs.get("renewal_within_60_days"):
        signals.append(
            f"Renewal in {hs.get('days_to_renewal')} days "
            f"({data.get('renewal_date')})"
        )
    if hs.get("contract_at_risk"):
        signals.append(f"Contract status is {data.get('contract_status')}")
    notes = (data.get("account_notes") or "").strip()
    if notes:
        signals.append(f"CRM notes: {notes}")
    if data.get("account_owner"):
        signals.append(f"Owner: {data.get('account_owner')}")
    return signals


def _usage_signals(usage: dict[str, Any]) -> list[str]:
    if not usage.get("ok"):
        return []
    account = usage.get("account") or {}
    signals: list[str] = []
    trend = account.get("usage_trend")
    if trend:
        signals.append(f"Usage trend: {trend}")
    if account.get("usage_dropped_over_20_percent"):
        signals.append(
            f"Usage declined {account.get('usage_decline_percent')}% "
            "(over 20% threshold)"
        )
    elif account.get("usage_decline_percent") is not None:
        signals.append(
            f"Usage decline {account.get('usage_decline_percent')}% "
            f"(logins/30d: {account.get('login_frequency_30d')})"
        )
    if account.get("feature_adoption_percent") is not None:
        signals.append(
            f"Feature adoption: {account.get('feature_adoption_percent')}%"
        )
    source = account.get("data_source")
    if source == "mock" or usage.get("usage_account_id") != usage.get(
        "requested_account_id"
    ):
        signals.append(
            "Usage data is mock-mapped (not live product analytics)"
        )
    return signals


def _classify(crm: dict[str, Any], usage: dict[str, Any]) -> RiskLevel:
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))

    if not crm_ok and not usage_ok:
        return "NEEDS MANUAL REVIEW"

    action = False
    watch = False

    if crm_ok:
        hs = (crm.get("data") or {}).get("health_signals") or {}
        if hs.get("renewal_within_60_days") or hs.get("contract_at_risk"):
            action = True

    if usage_ok:
        account = usage.get("account") or {}
        if account.get("usage_dropped_over_20_percent"):
            action = True
        elif (account.get("usage_trend") or "").lower() in {
            "declining",
            "inactive",
        }:
            watch = True

    if action:
        return "ACTION NEEDED"
    if watch:
        return "WATCH"
    if crm_ok:
        return "HEALTHY"
    return "NEEDS MANUAL REVIEW"


def _next_action(risk: RiskLevel, crm: dict[str, Any]) -> str:
    if risk == "NEEDS MANUAL REVIEW":
        err = (crm.get("message") if not crm.get("ok") else None) or (
            "Retrieve missing CRM and/or product-usage data"
        )
        return err

    data = crm.get("data") or {}
    owner = data.get("account_owner") or "account owner"
    renewal = data.get("renewal_date") or "the renewal date"
    if risk == "ACTION NEEDED":
        return (
            f"{owner} should confirm exec sponsor and renewal path "
            f"before {renewal}. Human approval required before any "
            "customer-facing outreach."
        )
    if risk == "WATCH":
        return (
            f"{owner} should monitor usage/adoption over the next 2 weeks "
            "and schedule a check-in if decline continues."
        )
    return (
        f"{owner} can keep the current cadence; no urgent renewal action."
    )


def _why_it_matters(risk: RiskLevel, signals: list[str]) -> str:
    if risk == "ACTION NEEDED":
        return (
            "Multiple or high-priority warning signals require CSM "
            "attention before renewal or churn risk increases. "
            f"Signals: {'; '.join(signals)}"
        )
    if risk == "WATCH":
        return (
            "One meaningful warning signal exists; monitor closely. "
            f"Signals: {'; '.join(signals)}"
        )
    if risk == "HEALTHY":
        return "No urgent renewal or usage risk signals in available data."
    return "Required account data is missing, conflicting, or unavailable."


def build_account_health_report(
    account_id: str,
    crm: dict[str, Any],
    usage: dict[str, Any],
) -> str:
    """Format the required AccountPulse sections from tool payloads."""

    risk = _classify(crm, usage)
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))
    data = crm.get("data") if crm_ok else {}
    name = (data or {}).get("account_name") or account_id
    label = f"{name} ({account_id})"

    signals = _crm_signals(crm) + _usage_signals(usage)
    if not signals:
        signals = ["Insufficient tool data to list signals"]

    sources: list[str] = []
    if crm_ok:
        sources.append("get_crm_account_data")
    else:
        sources.append(
            f"get_crm_account_data ERROR: "
            f"{crm.get('error') or crm.get('message') or 'failed'}"
        )
    if usage_ok:
        sources.append("get_product_usage")
    else:
        sources.append(
            f"get_product_usage ERROR: "
            f"{usage.get('error') or usage.get('message') or 'failed'}"
        )
    sources.append("support tickets: unavailable")
    sources.append("communication activity: unavailable")

    manual_review: list[str] = [
        "Support tickets — tool not connected (NEEDS MANUAL REVIEW)",
        "Communication activity — tool not connected (NEEDS MANUAL REVIEW)",
    ]
    if not crm_ok:
        manual_review.insert(
            0,
            f"CRM data unavailable for {account_id}: "
            f"{crm.get('message') or crm.get('error')}",
        )
    if not usage_ok:
        manual_review.insert(
            0,
            f"Product usage unavailable for {account_id}: "
            f"{usage.get('message') or usage.get('error')}",
        )
    elif (usage.get("account") or {}).get("data_source") == "mock":
        manual_review.append(
            "Product usage is mock-mapped for this HubSpot company "
            "(treat as directional, not live product analytics)"
        )

    action_block = "*(none)*"
    watch_block = "*(none)*"
    healthy_block = "*(none)*"

    detail = "\n".join(
        [
            f"- Account: {label}",
            f"- Risk level: {risk}",
            f"- Key signals: {'; '.join(signals)}",
            f"- Why it matters: {_why_it_matters(risk, signals)}",
            f"- Recommended next action: {_next_action(risk, crm)}",
            f"- Sources: {'; '.join(sources)}",
            "- Human approval required: Yes",
        ]
    )
    healthy_detail = "\n".join(
        [
            f"- Account: {label}",
            f"- Key signals: {'; '.join(signals)}",
            f"- Sources: {'; '.join(sources)}",
        ]
    )

    if risk == "ACTION NEEDED":
        action_block = detail
    elif risk == "WATCH":
        watch_block = detail
    elif risk == "HEALTHY":
        healthy_block = healthy_detail

    if risk == "ACTION NEEDED":
        summary = (
            f"Prioritize {label}: renewal/contract risk needs attention "
            f"before {(data or {}).get('renewal_date') or 'renewal'}."
        )
    elif risk == "WATCH":
        summary = f"Keep {label} on the watch list; one warning signal is present."
    elif risk == "HEALTHY":
        summary = f"{label} looks stable on available CRM/usage signals."
    else:
        summary = (
            f"Cannot fully assess {label} until missing CRM/usage data "
            "is available."
        )

    return "\n".join(
        [
            "## 1. ACTION NEEDED",
            action_block,
            "",
            "## 2. WATCH",
            watch_block,
            "",
            "## 3. HEALTHY",
            healthy_block,
            "",
            "## 4. NEEDS MANUAL REVIEW",
            "\n".join(f"- {item}" for item in manual_review),
            "",
            "## 5. SUMMARY FOR CSM",
            summary,
        ]
    )


def analyze_account(account_id: str) -> str:
    """Fetch CRM + usage tools and build a deterministic health report."""

    account_id = (account_id or "").strip()
    if not account_id:
        return build_account_health_report(
            "",
            {
                "ok": False,
                "error": "invalid_account_id",
                "message": "account_id is required",
            },
            {
                "ok": False,
                "error": "invalid_account_id",
                "message": "account_id is required",
            },
        )

    crm = get_crm_account_data(account_id)
    usage = fetch_product_usage(account_id)
    return build_account_health_report(account_id, crm, usage)
