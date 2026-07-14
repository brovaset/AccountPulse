"""AccountPulse communication-activity tool."""

from typing import Any

from strands import tool

from tools.communications.mock_data import (
    HUBSPOT_TO_COMMUNICATION_ACCOUNT,
    MOCK_COMMUNICATION_ACTIVITY,
)


def fetch_communication_activity(account_id: str) -> dict[str, Any]:
    """Fetch mock communication-activity data for an account."""

    if not account_id or not account_id.strip():
        return {
            "ok": False,
            "error": "invalid_account_id",
            "message": "A valid account ID is required.",
        }

    normalized_account_id = account_id.strip()

    communication_account_id = HUBSPOT_TO_COMMUNICATION_ACCOUNT.get(
        normalized_account_id,
        normalized_account_id,
    )

    if normalized_account_id == "communication_error":
        return {
            "ok": False,
            "error": "communication_unavailable",
            "message": "The communication-activity service is temporarily unavailable.",
        }

    account_data = MOCK_COMMUNICATION_ACTIVITY.get(communication_account_id)

    if account_data is None:
        return {
            "ok": False,
            "error": "account_not_found",
            "message": "No communication-activity data was found for the requested account.",
        }

    return {
        "ok": True,
        "requested_account_id": normalized_account_id,
        "communication_account_id": communication_account_id,
        "account": account_data,
    }


@tool
def get_communication_activity(account_id: str) -> dict[str, Any]:
    """
    Retrieve communication and customer-sentiment signals for one account.

    Args:
        account_id: Customer account identifier, such as acc_001
            or a HubSpot company ID.

    Returns:
        Communication-activity signals or a structured error.
    """

    return fetch_communication_activity(account_id)
