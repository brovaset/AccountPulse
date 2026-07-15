"""Mock product-usage data for AccountPulse development and testing."""

HUBSPOT_TO_USAGE_ACCOUNT = {
    "333055649511": "acc_001",  # Northwind Analytics
    "332906103502": "acc_002",  # Brightleaf Retail
    "333057467115": "acc_003",  # Harbor Logistics
}

MOCK_PRODUCT_USAGE = {
    "acc_001": {
        "account_id": "acc_001",
        "last_active_date": "2026-07-10",
        "login_frequency_30d": 24,
        "usage_trend": "stable",
        "feature_adoption_percent": 78,
        "usage_decline_percent": 5,
        "usage_dropped_over_20_percent": False,
        "data_source": "mock",
    },
    "acc_002": {
        "account_id": "acc_002",
        "last_active_date": "2026-07-08",
        "login_frequency_30d": 11,
        "usage_trend": "declining",
        "feature_adoption_percent": 42,
        "usage_decline_percent": 31,
        "usage_dropped_over_20_percent": True,
        "data_source": "mock",
    },
    "acc_003": {
        "account_id": "acc_003",
        "last_active_date": "2026-06-18",
        "login_frequency_30d": 1,
        "usage_trend": "inactive",
        "feature_adoption_percent": 15,
        "usage_decline_percent": 64,
        "usage_dropped_over_20_percent": True,
        "data_source": "mock",
    },
    "acc_004": {
        "account_id": "acc_004",
        "last_active_date": "2026-07-09",
        "login_frequency_30d": 18,
        "usage_trend": "stable",
        "feature_adoption_percent": 61,
        "usage_decline_percent": 8,
        "usage_dropped_over_20_percent": False,
        "data_source": "mock",
    },
    "acc_006": {
        "account_id": "acc_006",
        "last_active_date": "2026-07-12",
        "login_frequency_30d": 36,
        "usage_trend": "stable",
        "feature_adoption_percent": 87,
        "usage_decline_percent": 0,
        "usage_dropped_over_20_percent": False,
        "data_source": "mock",
    },
}