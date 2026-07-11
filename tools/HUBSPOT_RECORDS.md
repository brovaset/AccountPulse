# Connect real HubSpot company records

Your HubSpot private app is currently **read-only** (create/update via API returns 403).  
Create/enrich companies in the HubSpot UI, then verify with the CRM tool.

## Bath field mapping → AccountPulse

| Bath field | HubSpot source | Tool field |
|------------|----------------|------------|
| Company name | Company `name` | `account_name` |
| Company owner | Company owner | `account_owner` |
| Plan / subscription | Company `type` (or `HUBSPOT_PROP_PLAN_TIER`) | `plan_tier` |
| Customer status | Company lifecycle stage | `customer_status` |
| Renewal date | Associated deal `closedate` (or `HUBSPOT_PROP_RENEWAL`) | `renewal_date` |
| Contract status | Deal stage + renewal window (or `HUBSPOT_PROP_CONTRACT_STATUS`) | `contract_status` |
| Account notes | Latest note, else company description | `account_notes` |

## Create test companies in HubSpot UI

Create (or edit) these three companies:

### 1) Northwind Analytics (at-risk / ACTION NEEDED candidate)
- **Name:** Northwind Analytics
- **Owner:** Adedoyin Ahoton (or your CSM user)
- **Type / plan:** Enterprise
- **Lifecycle stage:** Customer
- **Description / note:** Customer mentioned budget pressure ahead of renewal.
- **Deal:** name `Northwind Renewal`, close date ~45 days out, stage `Contract Sent`

### 2) Brightleaf Retail (HEALTHY candidate)
- **Name:** Brightleaf Retail
- **Owner:** your CSM user
- **Type / plan:** Growth
- **Lifecycle stage:** Customer
- **Note:** Q2 business review completed. Adoption looks strong.
- **Deal:** close date ~180 days out, stage `Closed Won`

### 3) Harbor Logistics (WATCH / ACTION NEEDED)
- **Name:** Harbor Logistics
- **Owner:** your CSM user
- **Type / plan:** Enterprise
- **Lifecycle stage:** Customer
- **Note:** Contract in renewal negotiation.
- **Deal:** close date ~28 days out, stage `Contract Sent`

After saving each company, copy the **Company ID** from the HubSpot URL  
(`.../company/XXXXXXXX/`) into `.env`:

```bash
HUBSPOT_TEST_COMPANY_ID=XXXXXXXX
```

## Verify

```bash
uv run python scripts/verify_hubspot_crm.py
```

Or pull one company:

```bash
uv run python -c "
from dotenv import load_dotenv
load_dotenv()
from tools.crm import get_crm_account_data
import json, os
print(json.dumps(get_crm_account_data(os.environ['HUBSPOT_TEST_COMPANY_ID']), indent=2))
"
```

## Optional: enable API writes later

In the HubSpot private app, add write scopes (companies/deals/notes) if you want seeding via API instead of the UI.
