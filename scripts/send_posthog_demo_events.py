#!/usr/bin/env python3
"""Send demo PostHog $pageview events tagged with account_id for AccountPulse."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    project_key = os.getenv("POSTHOG_PROJECT_API_KEY", "").strip()
    if not project_key:
        print(
            "Missing POSTHOG_PROJECT_API_KEY in .env.\n"
            "Get it from PostHog → Project Settings → Project API Key (phc_...)."
        )
        return 1

    host = os.getenv("POSTHOG_HOST", "https://us.posthog.com").strip().rstrip("/")
    # Capture ingest host differs from app host on US/EU cloud.
    if "eu.posthog.com" in host:
        ingest = "https://eu.i.posthog.com"
    else:
        ingest = "https://us.i.posthog.com"

    account_id = (sys.argv[1] if len(sys.argv) > 1 else "acc_001").strip()
    event = os.getenv("POSTHOG_EVENT", "$pageview").strip() or "$pageview"
    now = datetime.now(timezone.utc).isoformat()

    # A few events so login_frequency_30d > 0 and trend can be computed.
    batch = []
    for i in range(1, 6):
        batch.append(
            {
                "event": event,
                "distinct_id": f"demo-user-{account_id}-{i % 2 + 1}",
                "timestamp": now,
                "properties": {
                    "account_id": account_id,
                    "source": "accountpulse_demo",
                    "demo_index": i,
                },
            }
        )

    payload = {
        "api_key": project_key,
        "batch": batch,
    }
    req = urllib.request.Request(
        f"{ingest}/batch/",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            print(f"Sent {len(batch)} '{event}' events for account_id={account_id}")
            print(f"ingest={ingest} status={resp.status} body={body[:200]}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"PostHog capture failed HTTP {exc.code}: {detail[:300]}")
        return 1
    except urllib.error.URLError as exc:
        print(f"PostHog network error: {exc.reason}")
        return 1

    print(
        "Wait ~30–60s, then run:\n"
        'python -c "from dotenv import load_dotenv; load_dotenv(); '
        "from tools.usage import fetch_product_usage; "
        f'print(fetch_product_usage(\'{account_id}\'))"'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
