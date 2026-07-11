"""Tests for the AccountPulse product-usage tool."""

from tools.usage.get_product_usage import fetch_product_usage


def test_healthy_account():
    result = fetch_product_usage("acc_001")

    assert result["ok"] is True
    assert result["account"]["usage_trend"] == "stable"
    assert result["account"]["usage_dropped_over_20_percent"] is False


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