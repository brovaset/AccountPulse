"""Mock support-ticket data for AccountPulse development and testing."""

HUBSPOT_TO_SUPPORT_ACCOUNT = {
    "333055649511": "acc_001",  # Northwind Analytics
    "332906103502": "acc_002",  # Brightleaf Retail
    "333057467115": "acc_003",  # Harbor Logistics
}

MOCK_SUPPORT_TICKETS = {
    "acc_001": {
        "account_id": "acc_001",
        "open_ticket_count": 1,
        "oldest_ticket_age_days": 3,
        "highest_severity": "medium",
        "unresolved_high_severity_over_7_days": False,
        "ticket_trend": "stable",
        "recent_ticket_subjects": ["Dashboard export question"],
        "data_source": "mock",
    },
    "acc_002": {
        "account_id": "acc_002",
        "open_ticket_count": 4,
        "oldest_ticket_age_days": 12,
        "highest_severity": "high",
        "unresolved_high_severity_over_7_days": True,
        "ticket_trend": "increasing",
        "recent_ticket_subjects": [
            "Checkout timeout",
            "API authentication failures",
            "Inventory sync delay",
        ],
        "data_source": "mock",
    },
    "acc_003": {
        "account_id": "acc_003",
        "open_ticket_count": 0,
        "oldest_ticket_age_days": 0,
        "highest_severity": "none",
        "unresolved_high_severity_over_7_days": False,
        "ticket_trend": "none",
        "recent_ticket_subjects": [],
        "data_source": "mock",
    },
}
