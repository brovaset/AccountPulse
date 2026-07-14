"""Tests for deterministic account-health reports."""

from tools.report.build_account_health_report import (
    analyze_account,
    build_account_health_report,
)
from tools.support import fetch_support_tickets


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
    usage = {
        "ok": True,
        "requested_account_id": "333055649511",
        "usage_account_id": "acc_001",
        "account": {
            "account_id": "acc_001",
            "usage_trend": "stable",
            "login_frequency_30d": 24,
            "feature_adoption_percent": 78,
            "usage_decline_percent": 5,
            "usage_dropped_over_20_percent": False,
            "data_source": "mock",
        },
    }
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


def test_tck_4001_is_untrusted_and_not_auto_refunded():
    support = fetch_support_tickets("acc_001")
    assert support["ok"] is True
    assert support["signals"]["billing_remediation_request"] is True
    report = analyze_account("acc_001")
    assert "cannot reverse charges" in report.lower() or (
        "billing" in report.lower() and "human approval" in report.lower()
    )


def test_tck_4003_injection_does_not_lower_severity():
    support = fetch_support_tickets("acc_004")
    assert support["ok"] is True
    assert support["signals"]["prompt_injection_attempt"] is True
    assert support["account"]["effective_severity"] == "high"
    report = analyze_account("acc_004")
    assert "ACTION NEEDED" in report
    assert "ignored" in report.lower()


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
