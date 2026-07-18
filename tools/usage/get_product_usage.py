"""AccountPulse product-usage tool (mock + PostHog; optional Gainsight)."""

from __future__ import annotations

import os
from typing import Any

from strands import tool

from tools.usage.gainsight_client import (
    GainsightClientError,
    fetch_gainsight_usage_account,
    gainsight_enabled,
)
from tools.usage.mock_data import (
    HUBSPOT_TO_USAGE_ACCOUNT,
    MOCK_PRODUCT_USAGE,
)
from tools.usage.posthog_client import (
    PostHogClientError,
    fetch_posthog_usage_account,
    posthog_enabled,
)


def _fetch_mock(normalized_account_id: str) -> dict[str, Any]:
    usage_account_id = HUBSPOT_TO_USAGE_ACCOUNT.get(
        normalized_account_id,
        normalized_account_id,
    )
    if normalized_account_id == "acc_error":
        return {
            "ok": False,
            "error": "usage_service_unavailable",
            "message": "The product-usage service is temporarily unavailable.",
        }
    account_data = MOCK_PRODUCT_USAGE.get(usage_account_id)
    if account_data is None:
        return {
            "ok": False,
            "error": "account_not_found",
            "message": (
                f"No product-usage data was found for "
                f"{normalized_account_id}."
            ),
            "account_id": normalized_account_id,
        }
    return {
        "ok": True,
        "requested_account_id": normalized_account_id,
        "usage_account_id": usage_account_id,
        "account": account_data,
    }


def _success(account_id: str, account: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "requested_account_id": account_id,
        "usage_account_id": account_id,
        "account": account,
    }


def _failure(account_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": code
        if code in {"account_not_found", "usage_service_unavailable"}
        else "usage_service_unavailable",
        "message": message,
        "requested_account_id": account_id,
        "account_id": account_id,
    }


def fetch_product_usage(account_id: str) -> dict[str, Any]:
    """Fetch product-usage data (PostHog/Gainsight when enabled, else mock)."""

    if not account_id or not account_id.strip():
        return {
            "ok": False,
            "error": "invalid_account_id",
            "message": "A valid account ID is required.",
        }

    normalized_account_id = account_id.strip()
    if os.getenv("USAGE_FORCE_ERROR", "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }:
        return {
            "ok": False,
            "error": "usage_service_unavailable",
            "message": "The product-usage service is temporarily unavailable.",
            "requested_account_id": normalized_account_id,
        }

    # Prefer PostHog (free tier). Gainsight remains optional if explicitly set.
    if posthog_enabled():
        try:
            return _success(
                normalized_account_id,
                fetch_posthog_usage_account(normalized_account_id),
            )
        except PostHogClientError as exc:
            return _failure(normalized_account_id, exc.code, exc.message)

    if gainsight_enabled():
        try:
            return _success(
                normalized_account_id,
                fetch_gainsight_usage_account(normalized_account_id),
            )
        except GainsightClientError as exc:
            return _failure(normalized_account_id, exc.code, exc.message)

    return _fetch_mock(normalized_account_id)


@tool
def get_product_usage(account_id: str) -> dict[str, Any]:
    """
    Retrieve product-usage signals for one customer account.

    Args:
        account_id: Customer account identifier, such as acc_001
            or a HubSpot company ID.

    Returns:
        Product-usage signals or a structured error.
    """

    return fetch_product_usage(account_id)
