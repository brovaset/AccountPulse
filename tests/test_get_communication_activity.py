"""Tests for the AccountPulse communication-activity tool."""

from tools.communications.get_communication_activity import (
    fetch_communication_activity,
)


def test_concerned_declining_communication_account():
    result = fetch_communication_activity("acc_001")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_001"
    assert result["communication_account_id"] == "acc_001"
    assert result["account"]["sentiment"] == "concerned"
    assert result["account"]["no_meaningful_contact_over_14_days"] is True


def test_active_positive_communication_account():
    result = fetch_communication_activity("acc_002")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_002"
    assert result["communication_account_id"] == "acc_002"
    assert result["account"]["sentiment"] == "positive"
    assert result["account"]["communication_trend"] == "active"


def test_limited_contact_account():
    result = fetch_communication_activity("acc_003")

    assert result["ok"] is True
    assert result["requested_account_id"] == "acc_003"
    assert result["communication_account_id"] == "acc_003"
    assert result["account"]["days_since_last_meaningful_contact"] == 15
    assert result["account"]["recent_meeting_count_30d"] == 0


def test_unknown_account():
    result = fetch_communication_activity("acc_999")

    assert result["ok"] is False
    assert result["error"] == "account_not_found"


def test_blank_account_id():
    result = fetch_communication_activity("   ")

    assert result["ok"] is False
    assert result["error"] == "invalid_account_id"


def test_communication_service_failure():
    result = fetch_communication_activity("communication_error")

    assert result["ok"] is False
    assert result["error"] == "communication_unavailable"


def test_northwind_hubspot_id_maps_to_acc_001():
    result = fetch_communication_activity("333055649511")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333055649511"
    assert result["communication_account_id"] == "acc_001"
    assert result["account"]["sentiment"] == "concerned"


def test_brightleaf_hubspot_id_maps_to_acc_002():
    result = fetch_communication_activity("332906103502")

    assert result["ok"] is True
    assert result["requested_account_id"] == "332906103502"
    assert result["communication_account_id"] == "acc_002"
    assert result["account"]["sentiment"] == "positive"


def test_harbor_hubspot_id_maps_to_acc_003():
    result = fetch_communication_activity("333057467115")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333057467115"
    assert result["communication_account_id"] == "acc_003"
    assert result["account"]["days_since_last_meaningful_contact"] == 15
