"""Tests for the AccountPulse support-ticket tool."""

from tools.support.get_support_tickets import fetch_support_tickets


def test_healthy_stable_support_account():
    result = fetch_support_tickets("acc_001")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_001"
    assert result["support_account_id"] == "acc_001"
    assert result["account"]["open_ticket_count"] == 1
    assert result["account"]["ticket_trend"] == "stable"


def test_high_risk_support_account():
    result = fetch_support_tickets("acc_002")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_002"
    assert result["support_account_id"] == "acc_002"
    assert result["account"]["highest_severity"] == "high"
    assert result["account"]["unresolved_high_severity_over_7_days"] is True


def test_no_ticket_account():
    result = fetch_support_tickets("acc_003")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_003"
    assert result["support_account_id"] == "acc_003"
    assert result["account"]["open_ticket_count"] == 0
    assert result["account"]["recent_ticket_subjects"] == []


def test_unknown_account():
    result = fetch_support_tickets("acc_999")

    assert result["ok"] is False
    assert result["error"] == "account_not_found"


def test_blank_account_id():
    result = fetch_support_tickets("   ")

    assert result["ok"] is False
    assert result["error"] == "invalid_account_id"


def test_support_service_failure():
    result = fetch_support_tickets("support_error")

    assert result["ok"] is False
    assert result["error"] == "support_unavailable"


def test_northwind_hubspot_id_maps_to_acc_001():
    result = fetch_support_tickets("333055649511")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333055649511"
    assert result["support_account_id"] == "acc_001"
    assert result["account"]["ticket_trend"] == "stable"


def test_brightleaf_hubspot_id_maps_to_acc_002():
    result = fetch_support_tickets("332906103502")

    assert result["ok"] is True
    assert result["requested_account_id"] == "332906103502"
    assert result["support_account_id"] == "acc_002"
    assert result["account"]["highest_severity"] == "high"


def test_harbor_hubspot_id_maps_to_acc_003():
    result = fetch_support_tickets("333057467115")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333057467115"
    assert result["support_account_id"] == "acc_003"
    assert result["account"]["open_ticket_count"] == 0
