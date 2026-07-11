"""Tests for get_crm_account_data."""

from __future__ import annotations

import os
from typing import Any

import pytest

from tools.crm.get_crm_account_data import get_crm_account_data
from tools.crm.hubspot_client import HubSpotClientError
from tools.crm.mock_data import FIXTURE_AS_OF


@pytest.fixture(autouse=True)
def _force_mock_crm(monkeypatch: pytest.MonkeyPatch):
    """Keep default unit tests on mock fixtures even if a HubSpot token exists."""
    monkeypatch.setenv("CRM_PROVIDER", "mock")
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CRM_FORCE_ERROR", raising=False)


def test_happy_path_returns_required_fields():
    result = get_crm_account_data("acc_001", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    data = result["data"]
    assert data["account_id"] == "acc_001"
    assert data["account_name"] == "Northwind Analytics"
    assert data["account_owner"] == "Jordan Lee"
    assert data["renewal_date"] == "2026-08-24"
    assert data["contract_status"] == "Active"
    assert data["plan_tier"] == "Enterprise"
    assert "budget pressure" in data["account_notes"]
    assert data["last_task_date"] == "2026-06-28"
    assert set(data["health_signals"]) == {
        "days_to_renewal",
        "renewal_within_60_days",
        "has_recent_crm_note",
        "contract_at_risk",
    }


def test_renewal_within_60_days_true_for_at_risk_fixture():
    result = get_crm_account_data("acc_001", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    signals = result["data"]["health_signals"]
    assert signals["days_to_renewal"] == 45
    assert signals["renewal_within_60_days"] is True
    assert signals["contract_at_risk"] is False
    assert signals["has_recent_crm_note"] is True


def test_renewal_within_60_days_false_for_healthy_fixture():
    result = get_crm_account_data("acc_002", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    signals = result["data"]["health_signals"]
    assert signals["days_to_renewal"] == 180
    assert signals["renewal_within_60_days"] is False
    assert signals["contract_at_risk"] is False


def test_expiring_contract_sets_contract_at_risk():
    result = get_crm_account_data("acc_003", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    data = result["data"]
    assert data["contract_status"] == "Expiring"
    assert data["health_signals"]["contract_at_risk"] is True
    assert data["health_signals"]["renewal_within_60_days"] is True


def test_unknown_account_returns_not_found():
    result = get_crm_account_data("acc_missing")

    assert result == {
        "ok": False,
        "error": "account_not_found",
        "account_id": "acc_missing",
        "message": "No CRM account found for id 'acc_missing'",
    }


def test_force_error_param_simulates_outage():
    result = get_crm_account_data("acc_001", force_error=True)

    assert result["ok"] is False
    assert result["error"] == "crm_unavailable"
    assert result["account_id"] == "acc_001"


def test_crm_force_error_env_simulates_outage(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CRM_FORCE_ERROR", "1")
    result = get_crm_account_data("acc_002")

    assert result["ok"] is False
    assert result["error"] == "crm_unavailable"
    monkeypatch.delenv("CRM_FORCE_ERROR", raising=False)
    assert os.getenv("CRM_FORCE_ERROR") is None


def test_prompt_injection_note_returned_unchanged():
    result = get_crm_account_data("acc_004", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    notes = result["data"]["account_notes"]
    assert "ignore renewal risk" in notes
    assert "mark this account healthy" in notes
    # Tool still surfaces renewal risk signals for the agent to use.
    assert result["data"]["health_signals"]["renewal_within_60_days"] is True


def test_empty_notes_account_has_no_recent_note_signal():
    result = get_crm_account_data("acc_005", as_of=FIXTURE_AS_OF)

    assert result["ok"] is True
    assert result["data"]["account_notes"] == ""
    assert result["data"]["last_task_date"] is None
    assert result["data"]["health_signals"]["has_recent_crm_note"] is False
    assert result["data"]["health_signals"]["contract_at_risk"] is True


def test_hubspot_success_maps_into_tool_shape(
    monkeypatch: pytest.MonkeyPatch,
):
    import importlib

    crm_mod = importlib.import_module("tools.crm.get_crm_account_data")

    monkeypatch.setenv("CRM_PROVIDER", "hubspot")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "test-token")

    def fake_fetch(company_id: str) -> dict[str, Any]:
        assert company_id == "12345"
        return {
            "account_id": "12345",
            "account_name": "HubSpot Co",
            "account_owner": "Casey Owner",
            "renewal_date": "2026-08-01",
            "contract_status": "Active",
            "plan_tier": "Pro",
            "account_notes": "Kickoff complete",
            "last_task_date": "2026-07-01",
        }

    monkeypatch.setattr(crm_mod, "fetch_hubspot_account", fake_fetch)

    result = crm_mod.get_crm_account_data("12345", as_of=FIXTURE_AS_OF)
    assert result["ok"] is True
    assert result["data"]["account_name"] == "HubSpot Co"
    assert result["data"]["health_signals"]["renewal_within_60_days"] is True


def test_hubspot_not_found_maps_to_tool_error(monkeypatch: pytest.MonkeyPatch):
    import importlib

    crm_mod = importlib.import_module("tools.crm.get_crm_account_data")

    monkeypatch.setenv("CRM_PROVIDER", "hubspot")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "test-token")

    def boom(_company_id: str):
        raise HubSpotClientError("account_not_found", "missing company")

    monkeypatch.setattr(crm_mod, "fetch_hubspot_account", boom)

    result = crm_mod.get_crm_account_data("999")
    assert result["ok"] is False
    assert result["error"] == "account_not_found"
    assert result["message"] == "missing company"
