"""Tests for Phase 2 multi-account morning briefing."""

from tools.crm.mock_data import list_mock_account_ids
from tools.report import (
    analyze_portfolio,
    analyze_portfolio_bundle,
    resolve_portfolio_account_ids,
)


def test_resolve_portfolio_defaults_to_all_mock_accounts():
    ids = resolve_portfolio_account_ids()
    assert ids == list_mock_account_ids()
    assert len(ids) >= 2


def test_resolve_portfolio_filters_by_owner():
    ids = resolve_portfolio_account_ids(owner="Jordan Lee")
    assert ids == ["acc_001", "acc_004"]


def test_analyze_portfolio_ranks_multiple_accounts():
    report = analyze_portfolio(["acc_001", "acc_006", "acc_005"])

    assert report.startswith("# AccountPulse morning briefing")
    assert "Reviewed **3** assigned account(s)" in report
    assert "## 1. ACTION NEEDED" in report
    assert "## 2. WATCH" in report
    assert "## 3. HEALTHY" in report
    assert "## 4. NEEDS MANUAL REVIEW" in report
    assert "## 5. SUMMARY FOR CSM" in report

    assert "Northwind Analytics" in report
    assert "Meridian Analytics" in report
    assert "Human approval required" in report

    action = report.split("## 1. ACTION NEEDED", 1)[1].split("## 2.", 1)[0]
    watch = report.split("## 2. WATCH", 1)[1].split("## 3.", 1)[0]
    assert "Northwind Analytics" in action
    assert "Meridian Analytics" in watch


def test_analyze_portfolio_bundle_counts_and_order():
    bundle = analyze_portfolio_bundle(["acc_001", "acc_006", "acc_003"])
    assert bundle["account_ids"] == ["acc_001", "acc_006", "acc_003"]
    assert len(bundle["accounts"]) == 3
    assert sum(bundle["counts"].values()) == 3
    assert bundle["counts"]["ACTION NEEDED"] >= 1
    assert bundle["counts"]["WATCH"] >= 1

    # Sooner renewals should rank higher within ACTION NEEDED.
    action_accounts = [
        item
        for item in bundle["accounts"]
        if item["risk"] == "ACTION NEEDED"
    ]
    if len(action_accounts) >= 2:
        days = [
            (item.get("crm") or {})
            .get("data", {})
            .get("health_signals", {})
            .get("days_to_renewal", 10_000)
            for item in sorted(
                action_accounts,
                key=lambda b: (
                    (b.get("crm") or {})
                    .get("data", {})
                    .get("health_signals", {})
                    .get("days_to_renewal", 10_000)
                ),
            )
        ]
        assert days == sorted(days)


def test_owner_briefing_covers_jordan_lee_book():
    report = analyze_portfolio(owner="Jordan Lee")
    assert "Northwind Analytics" in report
    assert "Summit Health Group" in report
    assert "Meridian Analytics" not in report
    assert "Reviewed **2** assigned account(s)" in report
