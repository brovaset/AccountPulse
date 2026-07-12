"""Tests for deterministic account-health reports."""

from tools.report.build_account_health_report import (
    analyze_account,
    build_account_health_report,
)


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

    report = build_account_health_report("333055649511", crm, usage)
    assert "## 1. ACTION NEEDED" in report
    assert "Northwind Analytics" in report
    assert "budget pressure" in report
    assert "2026-08-25" in report
    assert "missing account" not in report.lower()
    assert "retrieve the missing account data" not in report.lower()
    assert "NEEDS MANUAL REVIEW" in report
    assert "support tickets" in report.lower()


def test_analyze_account_mock_acc_001():
    report = analyze_account("acc_001")
    assert "ACTION NEEDED" in report
    assert "acc_001" in report
