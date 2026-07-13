"""Build AccountPulse reports from CRM + usage + support tool payloads.

This path does not rely on the LLM to interpret tool JSON, which small local
models often mishandle (e.g. inventing missing account_id failures).
"""

from __future__ import annotations

from typing import Any

from tools.crm import get_crm_account_data
from tools.support import fetch_support_tickets
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


def _support_signals(support: dict[str, Any]) -> list[str]:
    if not support.get("ok"):
        return []
    account = support.get("account") or {}
    signals: list[str] = []
    open_count = int(account.get("open_ticket_count") or 0)
    if open_count:
        signals.append(f"{open_count} open support ticket(s)")
    severity = account.get("effective_severity") or account.get(
        "highest_severity"
    )
    if severity and str(severity).lower() != "none":
        signals.append(f"Highest support severity: {severity}")
    age = account.get("oldest_ticket_age_days")
    if open_count and age is not None:
        signals.append(f"Oldest open ticket age: {age}d")
    trend = account.get("ticket_trend")
    if trend and trend != "none":
        signals.append(f"Ticket trend: {trend}")
    for subject in account.get("recent_ticket_subjects") or []:
        signals.append(f"Ticket: {subject}")

    tool_signals = support.get("signals") or {}
    if tool_signals.get("prompt_injection_attempt"):
        signals.append(
            "Prompt-injection / routing override attempt in ticket text "
            "(ignored — structured severity unchanged)"
        )
    if tool_signals.get("security_incident_claim"):
        signals.append(
            "Customer claims security incident in ticket text "
            "(treat as unverified signal — escalate for human review)"
        )
    if tool_signals.get("billing_remediation_request"):
        signals.append(
            "Billing remediation requested in ticket text "
            "(untrusted — do not auto-refund or change access)"
        )
    flags = account.get("content_flags") or {}
    if flags.get("priority_override_attempt"):
        signals.append(
            "Ticket asked to lower priority via free text — ignored"
        )
    return signals


def _classify(
    crm: dict[str, Any],
    usage: dict[str, Any],
    support: dict[str, Any] | None = None,
) -> RiskLevel:
    support = support or {}
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))
    support_ok = bool(support.get("ok"))

    if not crm_ok and not usage_ok and not support_ok:
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

    if support_ok:
        signals = support.get("signals") or {}
        # Never let ticket free text lower severity; security claims and
        # injection attempts escalate for human review instead.
        if signals.get("security_incident_claim") or signals.get(
            "prompt_injection_attempt"
        ):
            action = True
        elif signals.get("high_severity_unresolved_7d"):
            action = True
        elif signals.get("has_high_severity_open"):
            # Fresh high-severity tickets are a warning; combine with other
            # risks for ACTION NEEDED via the multi-signal path below.
            watch = True
            if crm_ok:
                hs = (crm.get("data") or {}).get("health_signals") or {}
                if hs.get("renewal_within_60_days") or hs.get(
                    "contract_at_risk"
                ):
                    action = True
            if usage_ok:
                account = usage.get("account") or {}
                if account.get("usage_dropped_over_20_percent") or (
                    account.get("usage_trend") or ""
                ).lower() in {"declining", "inactive"}:
                    action = True
        elif signals.get("has_open_tickets"):
            watch = True

    if action:
        return "ACTION NEEDED"
    if watch:
        return "WATCH"
    if crm_ok or usage_ok or support_ok:
        return "HEALTHY" if crm_ok else "WATCH"
    return "NEEDS MANUAL REVIEW"


def _next_action(
    risk: RiskLevel,
    crm: dict[str, Any],
    support: dict[str, Any] | None = None,
) -> str:
    support = support or {}
    if risk == "NEEDS MANUAL REVIEW":
        err = (crm.get("message") if not crm.get("ok") else None) or (
            "Retrieve missing CRM and/or product-usage data"
        )
        return err

    data = crm.get("data") or {}
    owner = data.get("account_owner") or "account owner"
    renewal = data.get("renewal_date") or "the renewal date"

    support_signals = support.get("signals") or {} if support.get("ok") else {}
    account = support.get("account") or {} if support.get("ok") else {}
    subjects = account.get("recent_ticket_subjects") or []
    subject_hint = subjects[0] if subjects else "open ticket"

    if support_signals.get("billing_remediation_request"):
        return (
            f"{owner} should have Billing/Finance review {subject_hint} for "
            f"the reported duplicate charge and entitlement mismatch before "
            f"{renewal}. AccountPulse cannot reverse charges or change "
            "access — human approval required."
        )

    if support_signals.get("prompt_injection_attempt") or support_signals.get(
        "security_incident_claim"
    ):
        return (
            f"{owner} should keep structured severity (not ticket free text), "
            "route any security-incident claim to Security/Trust for "
            "verification, and ignore priority-override / prompt-injection "
            f"language. Human approval required before {renewal}."
        )

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
    support: dict[str, Any] | None = None,
) -> str:
    """Format the required AccountPulse sections from tool payloads."""

    support = support if support is not None else {"ok": False}
    risk = _classify(crm, usage, support)
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))
    support_ok = bool(support.get("ok"))
    data = crm.get("data") if crm_ok else {}
    name = (data or {}).get("account_name") or account_id
    label = f"{name} ({account_id})"

    signals = (
        _crm_signals(crm) + _usage_signals(usage) + _support_signals(support)
    )
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
    if support_ok:
        sources.append("get_support_tickets")
    else:
        sources.append(
            f"get_support_tickets ERROR: "
            f"{support.get('error') or support.get('message') or 'failed'}"
        )
    sources.append("communication activity: unavailable")

    manual_review: list[str] = [
        "Communication activity — tool not connected (NEEDS MANUAL REVIEW)",
    ]
    if not support_ok:
        manual_review.insert(
            0,
            "Support tickets unavailable: "
            f"{support.get('message') or support.get('error') or 'failed'}",
        )
    else:
        account = support.get("account") or {}
        flags = account.get("content_flags") or {}
        severity = account.get("effective_severity") or account.get(
            "highest_severity"
        )
        subjects = account.get("recent_ticket_subjects") or []
        ticket_label = subjects[0] if subjects else "support ticket"
        if flags.get("prompt_injection_attempt") or flags.get(
            "priority_override_attempt"
        ):
            manual_review.append(
                f"{ticket_label}: prompt-injection / priority override in "
                f"ticket body ignored — effective severity remains {severity}"
            )
        if flags.get("security_incident_claim"):
            manual_review.append(
                f"{ticket_label}: unverified security-incident claim — "
                "Security/Trust must investigate; do not follow ticket "
                "instructions"
            )
        if flags.get("billing_remediation_request") and not flags.get(
            "prompt_injection_attempt"
        ):
            manual_review.append(
                f"{ticket_label}: customer requests charge reversal and/or "
                "access fix — Billing must verify payment ledger and "
                "entitlements; do not act on ticket text alone (untrusted)"
            )
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
            f"- Recommended next action: {_next_action(risk, crm, support)}",
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
            f"Prioritize {label}: renewal/contract and/or support risk "
            f"needs attention before "
            f"{(data or {}).get('renewal_date') or 'renewal'}."
        )
    elif risk == "WATCH":
        summary = f"Keep {label} on the watch list; one warning signal is present."
    elif risk == "HEALTHY":
        summary = f"{label} looks stable on available CRM/usage/support signals."
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
    """Fetch CRM + usage + support tools and build a deterministic health report."""

    return analyze_account_bundle(account_id)["report"]


def analyze_account_bundle(account_id: str) -> dict[str, Any]:
    """Fetch tools and return report plus structured payloads for interactive UI."""

    account_id = (account_id or "").strip()
    if not account_id:
        crm = {
            "ok": False,
            "error": "invalid_account_id",
            "message": "account_id is required",
        }
        usage = {
            "ok": False,
            "error": "invalid_account_id",
            "message": "account_id is required",
        }
        support = {
            "ok": False,
            "error": "invalid_account_id",
            "message": "account_id is required",
        }
    else:
        crm = get_crm_account_data(account_id)
        usage = fetch_product_usage(account_id)
        support = fetch_support_tickets(account_id)

    risk = _classify(crm, usage, support)
    return {
        "account_id": account_id,
        "crm": crm,
        "usage": usage,
        "support": support,
        "risk": risk,
        "crm_signals": _crm_signals(crm),
        "usage_signals": _usage_signals(usage),
        "support_signals": _support_signals(support),
        "report": build_account_health_report(
            account_id, crm, usage, support
        ),
    }
