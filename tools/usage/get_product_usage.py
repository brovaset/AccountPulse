"""AccountPulse product-usage tool."""

from typing import Any

from strands import tool

from tools.usage.mock_data import (
    HUBSPOT_TO_USAGE_ACCOUNT,
    MOCK_PRODUCT_USAGE,
)


def fetch_product_usage(account_id: str) -> dict[str, Any]:
    """Fetch mock product-usage data for an account."""

    if not account_id or not account_id.strip():
        return {
            "ok": False,
            "error": "invalid_account_id",
            "message": "A valid account ID is required.",
        }

    normalized_account_id = account_id.strip()

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