"""Tests for the AccountPulse product-usage tool."""

from tools.usage.get_product_usage import fetch_product_usage


def test_case1_golden_usage_account():
    result = fetch_product_usage("acc_001")

    assert result["ok"] is True
    assert result["account"]["usage_trend"] == "declining"
    assert result["account"]["usage_decline_percent"] >= 20
    assert result["account"]["usage_dropped_over_20_percent"] is True


def test_declining_account():
    result = fetch_product_usage("acc_002")

    assert result["ok"] is True
    assert result["account"]["usage_trend"] == "declining"
    assert result["account"]["usage_decline_percent"] == 31
    assert result["account"]["usage_dropped_over_20_percent"] is True


def test_inactive_account():
    result = fetch_product_usage("acc_003")

    assert result["ok"] is True
    assert result["account"]["usage_trend"] == "inactive"
    assert result["account"]["login_frequency_30d"] == 1


def test_unknown_account():
    result = fetch_product_usage("acc_999")

    assert result["ok"] is False
    assert result["error"] == "account_not_found"


def test_invalid_account_id():
    result = fetch_product_usage("")

    assert result["ok"] is False
    assert result["error"] == "invalid_account_id"


def test_usage_service_failure():
    result = fetch_product_usage("acc_error")

    assert result["ok"] is False
    assert result["error"] == "usage_service_unavailable"


def test_northwind_hubspot_id_maps_to_acc_001():
    result = fetch_product_usage("333055649511")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333055649511"
    assert result["usage_account_id"] == "acc_001"
    assert result["account"]["usage_trend"] == "declining"
    assert result["account"]["usage_dropped_over_20_percent"] is True


def test_brightleaf_hubspot_id_maps_to_acc_002():
    result = fetch_product_usage("332906103502")

    assert result["ok"] is True
    assert result["requested_account_id"] == "332906103502"
    assert result["usage_account_id"] == "acc_002"
    assert result["account"]["usage_trend"] == "declining"


def test_harbor_hubspot_id_maps_to_acc_003():
    result = fetch_product_usage("333057467115")

    assert result["ok"] is True
    assert result["requested_account_id"] == "333057467115"
    assert result["usage_account_id"] == "acc_003"
    assert result["account"]["usage_trend"] == "inactive"