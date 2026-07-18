"""Tests for Phase 3 Zendesk / Gainsight / Gmail provider wiring."""

from __future__ import annotations

import importlib

from tools.communications.get_communication_activity import (
    fetch_communication_activity,
)
from tools.communications.gmail_client import gmail_enabled
from tools.support.get_support_tickets import fetch_support_tickets
from tools.support.zendesk_client import ZendeskClientError, zendesk_enabled
from tools.usage.gainsight_client import gainsight_enabled
from tools.usage.get_product_usage import fetch_product_usage

support_mod = importlib.import_module("tools.support.get_support_tickets")
usage_mod = importlib.import_module("tools.usage.get_product_usage")
comms_mod = importlib.import_module("tools.communications.get_communication_activity")


def test_providers_disabled_without_credentials(monkeypatch):
    monkeypatch.delenv("SUPPORT_PROVIDER", raising=False)
    monkeypatch.delenv("ZENDESK_SUBDOMAIN", raising=False)
    monkeypatch.delenv("ZENDESK_EMAIL", raising=False)
    monkeypatch.delenv("ZENDESK_API_TOKEN", raising=False)
    monkeypatch.delenv("USAGE_PROVIDER", raising=False)
    monkeypatch.delenv("GAINSIGHT_ACCESS_KEY", raising=False)
    monkeypatch.delenv("GAINSIGHT_BASE_URL", raising=False)
    monkeypatch.delenv("COMMUNICATION_PROVIDER", raising=False)
    monkeypatch.delenv("GMAIL_ACCESS_TOKEN", raising=False)

    assert zendesk_enabled() is False
    assert gainsight_enabled() is False
    assert gmail_enabled() is False


def test_mock_still_default_for_acc_001(monkeypatch):
    monkeypatch.setenv("SUPPORT_PROVIDER", "mock")
    monkeypatch.setenv("USAGE_PROVIDER", "mock")
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "mock")

    support = fetch_support_tickets("acc_001")
    usage = fetch_product_usage("acc_001")
    comms = fetch_communication_activity("acc_001")

    assert support["ok"] is True
    assert support["account"]["data_source"] == "mock"
    assert usage["ok"] is True
    assert usage["account"]["data_source"] == "mock"
    assert comms["ok"] is True
    assert comms["account"].get("data_source") == "mock"


def test_zendesk_success_path(monkeypatch):
    monkeypatch.setenv("SUPPORT_PROVIDER", "zendesk")
    monkeypatch.setenv("ZENDESK_SUBDOMAIN", "example")
    monkeypatch.setenv("ZENDESK_EMAIL", "agent@example.com")
    monkeypatch.setenv("ZENDESK_API_TOKEN", "token")

    def fake_fetch(account_id: str):
        return {
            "account_id": account_id,
            "open_ticket_count": 1,
            "oldest_ticket_age_days": 9,
            "highest_severity": "high",
            "unresolved_high_severity_over_7_days": True,
            "ticket_trend": "stable",
            "recent_ticket_subjects": ["TCK-99: Billing issue"],
            "recent_ticket_bodies": ["Please reverse the charge"],
            "data_source": "zendesk",
        }

    monkeypatch.setattr(support_mod, "fetch_zendesk_support_account", fake_fetch)

    result = fetch_support_tickets("acc_001")
    assert result["ok"] is True
    assert result["account"]["data_source"] == "zendesk"
    assert result["signals"]["high_severity_unresolved_7d"] is True
    assert result["signals"]["billing_remediation_request"] is True


def test_zendesk_error_is_structured(monkeypatch):
    monkeypatch.setenv("SUPPORT_PROVIDER", "zendesk")
    monkeypatch.setenv("ZENDESK_SUBDOMAIN", "example")
    monkeypatch.setenv("ZENDESK_EMAIL", "agent@example.com")
    monkeypatch.setenv("ZENDESK_API_TOKEN", "token")

    def raise_boom(_account_id: str):
        raise ZendeskClientError("support_unavailable", "Zendesk down")

    monkeypatch.setattr(support_mod, "fetch_zendesk_support_account", raise_boom)

    result = fetch_support_tickets("acc_001")
    assert result["ok"] is False
    assert result["error"] == "support_unavailable"


def test_gainsight_success_path(monkeypatch):
    monkeypatch.setenv("USAGE_PROVIDER", "gainsight")
    monkeypatch.setenv("GAINSIGHT_BASE_URL", "https://example.gainsightcloud.com")
    monkeypatch.setenv("GAINSIGHT_ACCESS_KEY", "key")

    def fake_fetch(account_id: str):
        return {
            "account_id": account_id,
            "last_active_date": "2026-07-10",
            "login_frequency_30d": 10,
            "usage_trend": "declining",
            "feature_adoption_percent": 40,
            "usage_decline_percent": 25,
            "usage_dropped_over_20_percent": True,
            "data_source": "gainsight",
        }

    monkeypatch.setattr(usage_mod, "fetch_gainsight_usage_account", fake_fetch)

    result = fetch_product_usage("acc_001")
    assert result["ok"] is True
    assert result["account"]["data_source"] == "gainsight"
    assert result["account"]["usage_dropped_over_20_percent"] is True


def test_gmail_success_path(monkeypatch):
    monkeypatch.setenv("COMMUNICATION_PROVIDER", "gmail")
    monkeypatch.setenv("GMAIL_ACCESS_TOKEN", "token")

    def fake_fetch(account_id: str):
        return {
            "account_id": account_id,
            "last_meaningful_contact_date": "2026-06-20",
            "days_since_last_meaningful_contact": 20,
            "recent_email_count_30d": 3,
            "recent_meeting_count_30d": 0,
            "sentiment": "concerned",
            "sentiment_score": -0.4,
            "communication_trend": "declining",
            "recent_summary": "Customer raised budget pressure",
            "no_meaningful_contact_over_14_days": True,
            "customer_requested_follow_up": True,
            "data_source": "gmail",
        }

    monkeypatch.setattr(comms_mod, "fetch_gmail_communication_account", fake_fetch)

    result = fetch_communication_activity("acc_001")
    assert result["ok"] is True
    assert result["account"]["data_source"] == "gmail"
    assert result["account"]["no_meaningful_contact_over_14_days"] is True
