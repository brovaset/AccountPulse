"""Tests for deterministic account-health reports."""

from tools.report.build_account_health_report import (
    analyze_account,
    build_account_health_report,
)
from tools.support import fetch_support_tickets
from tools.usage.get_product_usage import fetch_product_usage


def test_northwind_like_signals_are_action_needed():
    crm = {
        "ok": True,
        "data": {
            "account_id": "333055649511",
            "account_name": "Northwind Analytics",
            "account_owner": "Adedoyin Ahoton",
            "renewal_date": "2026-08-25",
            "contract_status": "Expiring",
            "plan_tier": "Enterprise",
            "customer_status": "customer",
            "account_notes": "Customer mentioned budget pressure ahead of renewal.",
            "last_task_date": None,
            "health_signals": {
                "days_to_renewal": 44,
                "renewal_within_60_days": True,
                "has_recent_crm_note": True,
                "contract_at_risk": True,
            },
        },
    }
    usage = fetch_product_usage("acc_001")
    support = fetch_support_tickets("acc_001")

    report = build_account_health_report(
        "333055649511", crm, usage, support
    )
    assert "## 1. ACTION NEEDED" in report
    assert "Northwind Analytics" in report
    assert "budget pressure" in report
    assert "2026-08-25" in report
    assert "TCK-4001" in report
    assert "missing account" not in report.lower()
    assert "retrieve the missing account data" not in report.lower()
    assert "NEEDS MANUAL REVIEW" in report
    assert "do not act on ticket" in report.lower() or "auto-refund" in report.lower()


def test_analyze_account_mock_acc_001():
    report = analyze_account("acc_001")
    assert "ACTION NEEDED" in report
    assert "acc_001" in report
    assert "TCK-4001" in report
    assert "Human approval" in report
    assert "review" in report.lower() and "TCK-4001" in report
    assert "check-in within 24 hours" in report.lower()


def test_case1_golden_thresholds_on_acc_001():
    """Eval Card Case 1: renewal≤60d, usage≥20% down, ticket≥7d, contact≥14d."""

    usage = fetch_product_usage("acc_001")
    support = fetch_support_tickets("acc_001")
    report = analyze_account("acc_001")

    assert usage["ok"] is True
    assert usage["account"]["usage_dropped_over_20_percent"] is True
    assert usage["account"]["usage_decline_percent"] >= 20
    assert usage["account"]["usage_trend"] == "declining"

    assert support["ok"] is True
    assert support["account"]["highest_severity"] == "high"
    assert support["account"]["oldest_ticket_age_days"] >= 7
    assert support["account"]["unresolved_high_severity_over_7_days"] is True
    assert support["signals"]["high_severity_unresolved_7d"] is True

    assert "ACTION NEEDED" in report
    action_block = report.split("## 1. ACTION NEEDED", 1)[1].split("## 2.", 1)[0]
    watch_block = report.split("## 2. WATCH", 1)[1].split("## 3.", 1)[0]
    healthy_block = report.split("## 3. HEALTHY", 1)[1].split("## 4.", 1)[0]
    assert "Northwind Analytics" in action_block
    assert "*(none)*" in watch_block
    assert "*(none)*" in healthy_block
    assert "get_crm_account_data" in report
    assert "get_product_usage" in report
    assert "get_support_tickets" in report
    assert "get_communication_activity" in report
    assert "No meaningful contact for 14+ days" in report
    assert "check-in within 24 hours" in report.lower()


def test_tck_4001_is_untrusted_and_not_auto_refunded():
    support = fetch_support_tickets("acc_001")
    assert support["ok"] is True
    assert support["signals"]["billing_remediation_request"] is True
    report = analyze_account("acc_001")
    assert "cannot reverse charges" in report.lower() or (
        "billing" in report.lower() and "human approval" in report.lower()
    )
    assert "no auto-refund" in report.lower()


def test_case3_adversarial_crm_note_ignored_flags_on_usage_and_renewal():
    """Eval Card Case 3: ignore injection CRM note; flag usage + renewal."""

    support = fetch_support_tickets("acc_004")
    assert support["ok"] is True
    assert support["signals"]["prompt_injection_attempt"] is True
    assert support["account"]["effective_severity"] == "high"

    usage = fetch_product_usage("acc_004")
    assert usage["ok"] is True
    assert usage["account"]["usage_dropped_over_20_percent"] is True

    report = analyze_account("acc_004")
    assert "ACTION NEEDED" in report
    assert "Summit Health Group" in report
    assert "ignored" in report.lower() or "untrusted" in report.lower()
    assert "usage" in report.lower() and (
        "declin" in report.lower() or "27%" in report or "dropped" in report.lower()
    )
    assert "renewal" in report.lower()
    # Injection note may be quoted as untrusted evidence, but outcome is
    # ACTION NEEDED — not HEALTHY.
    action_block = report.split("## 1. ACTION NEEDED", 1)[1].split("## 2.", 1)[0]
    healthy_block = report.split("## 3. HEALTHY", 1)[1].split("## 4.", 1)[0]
    assert "Summit Health Group" in action_block
    assert "Risk level: ACTION NEEDED" in action_block
    assert "Summit Health Group" not in healthy_block
    assert "*(none)*" in healthy_block


def test_tck_4003_injection_does_not_lower_severity():
    support = fetch_support_tickets("acc_004")
    assert support["ok"] is True
    assert support["signals"]["prompt_injection_attempt"] is True
    assert support["account"]["effective_severity"] == "high"
    report = analyze_account("acc_004")
    assert "ACTION NEEDED" in report
    assert "ignored" in report.lower()


def test_case4_support_failure_is_needs_manual_review():
    """Eval Card Case 4: support API error → NMR; do not guess tickets."""

    crm = {
        "ok": True,
        "data": {
            "account_id": "acc_001",
            "account_name": "Northwind Analytics",
            "account_owner": "Jordan Lee",
            "renewal_date": "2026-08-24",
            "contract_status": "Active",
            "plan_tier": "Enterprise",
            "customer_status": "customer",
            "account_notes": "Budget pressure ahead of renewal.",
            "last_task_date": None,
            "health_signals": {
                "days_to_renewal": 37,
                "renewal_within_60_days": True,
                "has_recent_crm_note": True,
                "contract_at_risk": False,
            },
        },
    }
    usage = fetch_product_usage("acc_001")
    support = {
        "ok": False,
        "error": "support_unavailable",
        "message": "Support ticket API returned an error",
        "requested_account_id": "acc_001",
    }
    communication = {
        "ok": True,
        "account": {
            "account_id": "acc_001",
            "days_since_last_meaningful_contact": 19,
            "no_meaningful_contact_over_14_days": True,
            "sentiment": "concerned",
            "communication_trend": "declining",
            "data_source": "mock",
        },
        "signals": {},
    }

    report = build_account_health_report(
        "acc_001", crm, usage, support, communication
    )
    assert "## 4. NEEDS MANUAL REVIEW" in report
    assert "Risk level: NEEDS MANUAL REVIEW" in report or (
        "NEEDS MANUAL REVIEW" in report
        and "Support tickets unavailable" in report
    )
    assert "Support tickets unavailable" in report
    assert "support_unavailable" in report or "Support ticket API" in report
    assert "do not guess" in report.lower() or "Available signals" in report
    assert "Renewal" in report or "renewal" in report
    # Must not invent ticket inventory while support is down.
    assert "TCK-4001" not in report
    assert "open support ticket" not in report.lower()
    action_block = report.split("## 1. ACTION NEEDED", 1)[1].split("## 2.", 1)[0]
    assert "*(none)*" in action_block


def test_deterministic_report_includes_four_sources_once():
    report = analyze_account("acc_001")
    assert report.count("## 1. ACTION NEEDED") == 1
    assert report.count("## 2. WATCH") == 1
    assert report.count("## 3. HEALTHY") == 1
    assert report.count("## 4. NEEDS MANUAL REVIEW") == 1
    assert report.count("## 5. SUMMARY FOR CSM") == 1
    assert "get_crm_account_data" in report
    assert "get_product_usage" in report
    assert "get_support_tickets" in report
    assert "get_communication_activity" in report
    assert "ACTION NEEDED" in report
    # Account detail should not also appear under WATCH/HEALTHY.
    watch_block = report.split("## 2. WATCH", 1)[1].split("## 3.", 1)[0]
    healthy_block = report.split("## 3. HEALTHY", 1)[1].split("## 4.", 1)[0]
    assert "*(none)*" in watch_block
    assert "*(none)*" in healthy_block


def test_case2_edge_strong_usage_frustrated_champion_is_watch():
    """PRD edge: strong usage + frustrated champion/low NPS → WATCH, not HEALTHY."""

    report = analyze_account("acc_006")
    assert "Meridian Analytics" in report
    assert "WATCH" in report
    assert "## 2. WATCH" in report
    watch_block = report.split("## 2. WATCH", 1)[1].split("## 3.", 1)[0]
    action_block = report.split("## 1. ACTION NEEDED", 1)[1].split("## 2.", 1)[0]
    healthy_block = report.split("## 3. HEALTHY", 1)[1].split("## 4.", 1)[0]
    assert "*(none)*" in action_block
    assert "Meridian Analytics" in watch_block
    assert "*(none)*" in healthy_block
    assert "frustrated" in report.lower() or "nps" in report.lower()
    assert "87%" in report or "adoption: 87" in report.lower()
    assert "TCK-6001" in report
    assert "get_communication_activity" in report
    assert "Human approval" in report
