"""Build AccountPulse reports from CRM + usage + support + communication payloads.

This path does not rely on the LLM to interpret tool JSON, which small local
models often mishandle (e.g. inventing missing account_id failures).
"""

from __future__ import annotations

from typing import Any

from tools.communications import fetch_communication_activity
from tools.crm import get_crm_account_data
from tools.crm.mock_data import list_mock_account_ids
from tools.support import fetch_support_tickets
from tools.usage.get_product_usage import fetch_product_usage

RiskLevel = str  # ACTION NEEDED | WATCH | HEALTHY | NEEDS MANUAL REVIEW

_PORTFOLIO_SECTION_ORDER = (
    "ACTION NEEDED",
    "WATCH",
    "HEALTHY",
    "NEEDS MANUAL REVIEW",
)


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


def _communication_signals(comms: dict[str, Any]) -> list[str]:
    if not comms.get("ok"):
        return []
    account = comms.get("account") or {}
    signals: list[str] = []
    days = account.get("days_since_last_meaningful_contact")
    if days is not None:
        signals.append(f"Days since last meaningful contact: {days}")
    if account.get("no_meaningful_contact_over_14_days"):
        signals.append("No meaningful contact for 14+ days")
    sentiment = account.get("sentiment")
    if sentiment:
        signals.append(f"Communication sentiment: {sentiment}")
    if account.get("nps_score") is not None:
        signals.append(f"NPS score: {account.get('nps_score')}")
    trend = account.get("communication_trend")
    if trend:
        signals.append(f"Communication trend: {trend}")
    summary = (account.get("recent_summary") or "").strip()
    if summary:
        signals.append(f"Recent communication summary: {summary}")
    if account.get("customer_requested_follow_up"):
        signals.append("Customer requested follow-up")
    if account.get("data_source") == "mock":
        signals.append(
            "Communication data is mock-mapped (not live mailbox/Gong)"
        )
    return signals


def _classify(
    crm: dict[str, Any],
    usage: dict[str, Any],
    support: dict[str, Any] | None = None,
    communication: dict[str, Any] | None = None,
) -> RiskLevel:
    support = support or {}
    communication = communication or {}
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))
    support_ok = bool(support.get("ok"))
    communication_ok = bool(communication.get("ok"))

    if not crm_ok and not usage_ok and not support_ok and not communication_ok:
        return "NEEDS MANUAL REVIEW"

    # Eval Card Case 4: support API failure with other sources available →
    # do not guess ticket status; require manual review.
    support_failed = (not support_ok) and bool(
        support.get("error") or support.get("message")
    )
    if support_failed and (crm_ok or usage_ok or communication_ok):
        return "NEEDS MANUAL REVIEW"

    action = False
    watch = False
    warning_count = 0

    if crm_ok:
        hs = (crm.get("data") or {}).get("health_signals") or {}
        if hs.get("renewal_within_60_days") or hs.get("contract_at_risk"):
            action = True
            warning_count += 1

    if usage_ok:
        account = usage.get("account") or {}
        if account.get("usage_dropped_over_20_percent"):
            action = True
            warning_count += 1
        elif (account.get("usage_trend") or "").lower() in {
            "declining",
            "inactive",
        }:
            watch = True
            warning_count += 1

    if support_ok:
        signals = support.get("signals") or {}
        # Never let ticket free text lower severity; security claims and
        # injection attempts escalate for human review instead.
        if signals.get("security_incident_claim") or signals.get(
            "prompt_injection_attempt"
        ):
            action = True
            warning_count += 1
        elif signals.get("high_severity_unresolved_7d"):
            action = True
            warning_count += 1
        elif signals.get("has_high_severity_open"):
            watch = True
            warning_count += 1
        elif signals.get("has_open_tickets"):
            # Non-high open tickets are a WATCH signal, but do not alone
            # push multi-signal ACTION NEEDED (keeps edge cases like
            # strong usage + frustrated champion + medium ticket as WATCH).
            watch = True

    if communication_ok:
        account = communication.get("account") or {}
        sentiment = (account.get("sentiment") or "").lower()
        trend = (account.get("communication_trend") or "").lower()
        nps = account.get("nps_score")
        relationship_risk = sentiment in {
            "concerned",
            "negative",
            "frustrated",
        } or (nps is not None and nps < 30)
        if account.get("no_meaningful_contact_over_14_days"):
            watch = True
            warning_count += 1
        if relationship_risk:
            # Frustrated/low NPS is one relationship warning (not two).
            watch = True
            warning_count += 1
        if trend in {"declining", "limited"}:
            watch = True
            warning_count += 1
        if account.get("customer_requested_follow_up"):
            watch = True

    # Multiple warning signals across systems => ACTION NEEDED.
    if warning_count >= 2:
        action = True

    if action:
        return "ACTION NEEDED"
    if watch:
        return "WATCH"
    if crm_ok or usage_ok or support_ok or communication_ok:
        return "HEALTHY" if crm_ok else "WATCH"
    return "NEEDS MANUAL REVIEW"


def _next_action(
    risk: RiskLevel,
    crm: dict[str, Any],
    support: dict[str, Any] | None = None,
    communication: dict[str, Any] | None = None,
) -> str:
    support = support or {}
    communication = communication or {}
    if risk == "NEEDS MANUAL REVIEW":
        err = (crm.get("message") if not crm.get("ok") else None) or (
            "Retrieve missing CRM and/or product-usage data"
        )
        return err

    data = crm.get("data") or {}
    owner = data.get("account_owner") or "account owner"
    renewal = data.get("renewal_date") or "the renewal date"
    hs = data.get("health_signals") or {}
    renewal_urgent = bool(hs.get("renewal_within_60_days"))

    comms = (
        communication.get("account") or {} if communication.get("ok") else {}
    )
    sentiment = (comms.get("sentiment") or "").lower()
    nps = comms.get("nps_score")
    relationship_risk = (
        sentiment in {"concerned", "negative", "frustrated"}
        or (nps is not None and nps < 30)
        or bool(comms.get("customer_requested_follow_up"))
    )

    support_signals = support.get("signals") or {} if support.get("ok") else {}
    billing = bool(support_signals.get("billing_remediation_request"))
    subjects = (support.get("account") or {}).get("recent_ticket_subjects") or []
    billing_ticket = subjects[0] if billing and subjects else None
    has_renewal_risk = renewal_urgent or relationship_risk

    if support_signals.get("prompt_injection_attempt") or support_signals.get(
        "security_incident_claim"
    ):
        return (
            f"{owner} should keep structured severity (not ticket free text), "
            "route any security-incident claim to Security/Trust for "
            "verification, and ignore priority-override / prompt-injection "
            f"language. Human approval required before {renewal}."
        )

    open_ticket = subjects[0] if subjects else None

    # Eval Card Case 1: review ticket + schedule check-in within hours.
    if open_ticket and (risk == "ACTION NEEDED" or has_renewal_risk):
        billing_note = (
            " Billing/Finance must verify any charge remediation "
            "(no auto-refund)."
            if billing
            else ""
        )
        return (
            f"{owner} should review {open_ticket} and schedule a customer "
            f"check-in within 24 hours.{billing_note} Human approval "
            f"required before {renewal}."
        )
    if billing_ticket:
        return (
            f"Billing/Finance verify {billing_ticket} (no auto-refund) — "
            "human approval required."
        )
    if risk == "ACTION NEEDED" or renewal_urgent:
        return (
            f"{owner} should confirm exec sponsor and schedule a check-in "
            f"before {renewal}. Human approval required before any "
            "customer-facing outreach."
        )
    if risk == "WATCH":
        if relationship_risk:
            return (
                f"{owner} should follow up on champion frustration / low NPS "
                "despite strong product usage — confirm support experience "
                "and relationship health. Human approval required before "
                "outreach."
            )
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
    communication: dict[str, Any] | None = None,
) -> str:
    """Format the required AccountPulse sections from tool payloads."""

    support = support if support is not None else {"ok": False}
    communication = (
        communication if communication is not None else {"ok": False}
    )
    risk = _classify(crm, usage, support, communication)
    crm_ok = bool(crm.get("ok"))
    usage_ok = bool(usage.get("ok"))
    support_ok = bool(support.get("ok"))
    communication_ok = bool(communication.get("ok"))
    data = crm.get("data") if crm_ok else {}
    name = (data or {}).get("account_name") or account_id
    label = f"{name} ({account_id})"

    signals = (
        _crm_signals(crm)
        + _usage_signals(usage)
        + _support_signals(support)
        + _communication_signals(communication)
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
    if communication_ok:
        sources.append("get_communication_activity")
    else:
        sources.append(
            f"get_communication_activity ERROR: "
            f"{communication.get('error') or communication.get('message') or 'failed'}"
        )

    manual_review: list[str] = []
    if not support_ok:
        manual_review.append(
            "Support tickets unavailable: "
            f"{support.get('message') or support.get('error') or 'failed'}"
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
    if not communication_ok:
        manual_review.append(
            "Communication activity unavailable: "
            f"{communication.get('message') or communication.get('error') or 'failed'}"
        )
    elif (communication.get("account") or {}).get("data_source") == "mock":
        manual_review.append(
            "Communication activity is mock-mapped for this account "
            "(treat as directional, not live mailbox/Gong)"
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
    if risk == "NEEDS MANUAL REVIEW" and signals:
        manual_review.insert(
            0,
            f"Available signals (incomplete — do not guess missing tools): "
            f"{'; '.join(signals)}",
        )
    if not manual_review:
        manual_review.append("*(none)*")

    action_block = "*(none)*"
    watch_block = "*(none)*"
    healthy_block = "*(none)*"

    detail = "\n".join(
        [
            f"- Account: {label}",
            f"- Risk level: {risk}",
            f"- Key signals: {'; '.join(signals)}",
            f"- Why it matters: {_why_it_matters(risk, signals)}",
            f"- Recommended next action: "
            f"{_next_action(risk, crm, support, communication)}",
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
            f"Prioritize {label}: renewal/contract, support, and/or "
            f"communication risk needs attention before "
            f"{(data or {}).get('renewal_date') or 'renewal'}."
        )
    elif risk == "WATCH":
        summary = f"Keep {label} on the watch list; one warning signal is present."
    elif risk == "HEALTHY":
        summary = (
            f"{label} looks stable on available CRM/usage/support/"
            "communication signals."
        )
    else:
        summary = (
            f"Cannot fully assess {label}: missing or conflicting tool data "
            "requires manual review before acting on incomplete signals."
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
    """Fetch all available tools and build a deterministic health report."""

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
        communication = {
            "ok": False,
            "error": "invalid_account_id",
            "message": "account_id is required",
        }
    else:
        crm = get_crm_account_data(account_id)
        usage = fetch_product_usage(account_id)
        support = fetch_support_tickets(account_id)
        communication = fetch_communication_activity(account_id)

    risk = _classify(crm, usage, support, communication)
    return {
        "account_id": account_id,
        "crm": crm,
        "usage": usage,
        "support": support,
        "communication": communication,
        "risk": risk,
        "crm_signals": _crm_signals(crm),
        "usage_signals": _usage_signals(usage),
        "support_signals": _support_signals(support),
        "communication_signals": _communication_signals(communication),
        "report": build_account_health_report(
            account_id, crm, usage, support, communication
        ),
    }


def resolve_portfolio_account_ids(
    account_ids: list[str] | None = None,
    owner: str | None = None,
) -> list[str]:
    """Resolve which accounts belong in a morning briefing."""

    if account_ids:
        return [aid.strip() for aid in account_ids if aid and str(aid).strip()]
    return list_mock_account_ids(owner=owner)


def _days_to_renewal(bundle: dict[str, Any]) -> int:
    hs = ((bundle.get("crm") or {}).get("data") or {}).get("health_signals") or {}
    days = hs.get("days_to_renewal")
    if isinstance(days, int):
        return days
    return 10_000


def _compact_portfolio_entry(bundle: dict[str, Any]) -> str:
    """One compact ranked entry for the morning briefing."""

    crm = bundle.get("crm") or {}
    data = crm.get("data") or {}
    account_id = bundle.get("account_id") or "unknown"
    name = data.get("account_name") or account_id
    owner = data.get("account_owner") or "—"
    renewal = data.get("renewal_date") or "—"
    risk = bundle.get("risk") or "NEEDS MANUAL REVIEW"
    signals = (
        list(bundle.get("crm_signals") or [])
        + list(bundle.get("usage_signals") or [])
        + list(bundle.get("support_signals") or [])
        + list(bundle.get("communication_signals") or [])
    )
    top = "; ".join(signals[:5]) if signals else "No structured signals available"
    next_action = _next_action(
        risk,
        crm,
        bundle.get("support") or {},
        bundle.get("communication") or {},
    )
    return "\n".join(
        [
            f"- **{name}** (`{account_id}`)",
            f"  - Risk level: {risk}",
            f"  - Owner: {owner}; Renewal: {renewal}",
            f"  - Top signals: {top}",
            f"  - Recommended next action: {next_action}",
            "  - Human approval required: Yes",
        ]
    )


def build_morning_briefing(bundles: list[dict[str, Any]]) -> str:
    """Merge per-account bundles into one prioritized CSM morning briefing."""

    buckets: dict[str, list[dict[str, Any]]] = {
        risk: [] for risk in _PORTFOLIO_SECTION_ORDER
    }
    for bundle in bundles:
        risk = bundle.get("risk") or "NEEDS MANUAL REVIEW"
        if risk not in buckets:
            risk = "NEEDS MANUAL REVIEW"
        buckets[risk].append(bundle)

    for risk in buckets:
        buckets[risk].sort(key=_days_to_renewal)

    sections: list[str] = ["# AccountPulse morning briefing", ""]
    counts = {risk: len(buckets[risk]) for risk in _PORTFOLIO_SECTION_ORDER}
    sections.append(
        f"Reviewed **{len(bundles)}** assigned account(s): "
        f"{counts['ACTION NEEDED']} ACTION NEEDED · "
        f"{counts['WATCH']} WATCH · "
        f"{counts['HEALTHY']} HEALTHY · "
        f"{counts['NEEDS MANUAL REVIEW']} NEEDS MANUAL REVIEW"
    )
    sections.append("")

    for index, risk in enumerate(_PORTFOLIO_SECTION_ORDER, start=1):
        sections.append(f"## {index}. {risk}")
        entries = buckets[risk]
        if not entries:
            sections.append("*(none)*")
        else:
            sections.append("\n\n".join(_compact_portfolio_entry(b) for b in entries))
        sections.append("")

    priority_names: list[str] = []
    for risk in ("ACTION NEEDED", "NEEDS MANUAL REVIEW", "WATCH"):
        for bundle in buckets[risk]:
            data = (bundle.get("crm") or {}).get("data") or {}
            label = data.get("account_name") or bundle.get("account_id")
            priority_names.append(f"{label} ({risk})")

    sections.append("## 5. SUMMARY FOR CSM")
    if priority_names:
        sections.append(
            "Work top-down: "
            + "; ".join(priority_names)
            + ". Verify evidence before any customer-facing action — "
            "human approval required."
        )
    else:
        sections.append(
            "No elevated-risk accounts in this briefing. Keep normal cadence; "
            "human approval still required before outreach."
        )

    return "\n".join(sections).rstrip() + "\n"


def analyze_portfolio_bundle(
    account_ids: list[str] | None = None,
    owner: str | None = None,
) -> dict[str, Any]:
    """Fetch and classify multiple accounts for a morning briefing."""

    resolved = resolve_portfolio_account_ids(account_ids=account_ids, owner=owner)
    bundles = [analyze_account_bundle(account_id) for account_id in resolved]
    report = build_morning_briefing(bundles)
    counts = {risk: 0 for risk in _PORTFOLIO_SECTION_ORDER}
    for bundle in bundles:
        risk = bundle.get("risk") or "NEEDS MANUAL REVIEW"
        if risk not in counts:
            risk = "NEEDS MANUAL REVIEW"
        counts[risk] += 1
    return {
        "account_ids": resolved,
        "owner": owner,
        "accounts": bundles,
        "counts": counts,
        "report": report,
    }


def analyze_portfolio(
    account_ids: list[str] | None = None,
    owner: str | None = None,
) -> str:
    """Return a prioritized multi-account morning briefing report."""

    return analyze_portfolio_bundle(account_ids=account_ids, owner=owner)["report"]
