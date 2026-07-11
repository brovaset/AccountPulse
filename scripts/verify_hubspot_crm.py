"""Verify live HubSpot companies through get_crm_account_data."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from tools.crm import get_crm_account_data
from tools.crm.hubspot_client import hubspot_enabled, list_hubspot_company_ids


def main() -> None:
    if not hubspot_enabled():
        raise SystemExit(
            "HubSpot is not enabled. Set HUBSPOT_ACCESS_TOKEN (and CRM_PROVIDER=auto|hubspot)."
        )

    companies = list_hubspot_company_ids(limit=20)
    if not companies:
        raise SystemExit(
            "No HubSpot companies found. Create companies in the HubSpot UI "
            "(see tools/HUBSPOT_RECORDS.md), then rerun."
        )

    print(f"Found {len(companies)} HubSpot companies\n")
    for row in companies:
        print(
            f"- {row['account_id']}: {row['account_name'] or '(unnamed)'} "
            f"[plan={row['plan_tier'] or '-'}, status={row['customer_status'] or '-'}]"
        )

    target = os.getenv("HUBSPOT_TEST_COMPANY_ID", "").strip() or companies[0]["account_id"]
    print(f"\nPulling get_crm_account_data({target!r})...\n")
    result = get_crm_account_data(target)
    print(json.dumps(result, indent=2))

    if not result.get("ok"):
        raise SystemExit(1)

    data = result["data"]
    missing = [
        field
        for field, value in {
            "account_owner": data.get("account_owner"),
            "plan_tier": data.get("plan_tier"),
            "customer_status": data.get("customer_status"),
            "account_notes": data.get("account_notes"),
        }.items()
        if not value or value in {"Unknown", "unknown"}
    ]
    if missing:
        print(
            "\nWarning: sparse fields "
            f"{missing}. Fill them in HubSpot UI per tools/HUBSPOT_RECORDS.md."
        )


if __name__ == "__main__":
    main()
