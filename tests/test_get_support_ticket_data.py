"""Tests for the mock support-ticket tool."""

from tools.support import fetch_support_ticket_data


def test_tck_4001_on_acc_001():
    result = fetch_support_ticket_data("acc_001")
    assert result["ok"] is True
    assert result["open_ticket_count"] == 1
    assert result["signals"]["has_high_severity_open"] is True
    assert result["signals"]["high_severity_unresolved_7d"] is False
    assert result["tickets"][0]["ticket_id"] == "TCK-4001"


def test_hubspot_northwind_maps_to_acc_001_support():
    result = fetch_support_ticket_data("333055649511")
    assert result["ok"] is True
    assert result["support_account_id"] == "acc_001"
    assert any(t["ticket_id"] == "TCK-4001" for t in result["tickets"])


def test_healthy_account_has_no_open_tickets():
    result = fetch_support_ticket_data("acc_002")
    assert result["ok"] is True
    assert result["open_ticket_count"] == 0
