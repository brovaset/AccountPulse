"""AccountPulse support-ticket tool."""

from typing import Any

from strands import tool

from tools.support.mock_data import (
    HUBSPOT_TO_SUPPORT_ACCOUNT,
    MOCK_SUPPORT_TICKETS,
)


def fetch_support_tickets(account_id: str) -> dict[str, Any]:
    """Fetch mock support-ticket data for an account."""

    if not account_id or not account_id.strip():
        return {
            "ok": False,
            "error": "invalid_account_id",
            "message": "A valid account ID is required.",
        }

    normalized_account_id = account_id.strip()

    support_account_id = HUBSPOT_TO_SUPPORT_ACCOUNT.get(
        normalized_account_id,
        normalized_account_id,
    )

    if normalized_account_id == "support_error":
        return {
            "ok": False,
            "error": "support_unavailable",
            "message": "The support-ticket service is temporarily unavailable.",
        }

    account_data = MOCK_SUPPORT_TICKETS.get(support_account_id)

    if account_data is None:
        return {
            "ok": False,
            "error": "account_not_found",
            "message": "No support-ticket data was found for the requested account.",
        }

    return {
        "ok": True,
        "requested_account_id": normalized_account_id,
        "support_account_id": support_account_id,
        "account": account_data,
    }


@tool
def get_support_tickets(account_id: str) -> dict[str, Any]:
    """
    Retrieve support-ticket signals for one customer account.

    Args:
        account_id: Customer account identifier, such as acc_001
            or a HubSpot company ID.

    Returns:
        Support-ticket signals or a structured error.
    """

    return fetch_support_tickets(account_id)
