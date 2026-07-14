"""Mock communication-activity data for AccountPulse development and testing."""

HUBSPOT_TO_COMMUNICATION_ACCOUNT = {
    "333055649511": "acc_001",  # Northwind Analytics
    "332906103502": "acc_002",  # Brightleaf Retail
    "333057467115": "acc_003",  # Harbor Logistics
}

MOCK_COMMUNICATION_ACTIVITY = {
    "acc_001": {
        "account_id": "acc_001",
        "last_meaningful_contact_date": "2026-06-24",
        "days_since_last_meaningful_contact": 19,
        "recent_email_count_30d": 2,
        "recent_meeting_count_30d": 1,
        "sentiment": "concerned",
        "sentiment_score": -0.45,
        "communication_trend": "declining",
        "recent_summary": "Customer raised budget pressure ahead of renewal and requested clearer value justification.",
        "no_meaningful_contact_over_14_days": True,
        "customer_requested_follow_up": True,
        "data_source": "mock",
    },
    "acc_002": {
        "account_id": "acc_002",
        "last_meaningful_contact_date": "2026-07-09",
        "days_since_last_meaningful_contact": 4,
        "recent_email_count_30d": 6,
        "recent_meeting_count_30d": 2,
        "sentiment": "positive",
        "sentiment_score": 0.72,
        "communication_trend": "active",
        "recent_summary": "Customer reported a positive rollout and confirmed progress toward adoption goals.",
        "no_meaningful_contact_over_14_days": False,
        "customer_requested_follow_up": False,
        "data_source": "mock",
    },
    "acc_003": {
        "account_id": "acc_003",
        "last_meaningful_contact_date": "2026-06-28",
        "days_since_last_meaningful_contact": 15,
        "recent_email_count_30d": 1,
        "recent_meeting_count_30d": 0,
        "sentiment": "neutral",
        "sentiment_score": 0.05,
        "communication_trend": "limited",
        "recent_summary": "Customer acknowledged the renewal notice but has not scheduled a follow-up meeting.",
        "no_meaningful_contact_over_14_days": True,
        "customer_requested_follow_up": False,
        "data_source": "mock",
    },
}
