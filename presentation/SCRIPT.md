# AccountPulse — 5-minute presentation script

## Timing

| Time | What |
|------|------|
| 0:00–0:45 | Problem + solution |
| 0:45–1:30 | Tools + deterministic flow |
| 1:30–4:00 | Live demo (`acc_001`) |
| 4:00–4:45 | Safety + human approval |
| 4:45–5:00 | Close + what’s next |

---

## 1. Problem

CSMs track renewal risk across CRM notes, product usage, support tickets, and customer communications. Those signals live in different systems, so “who needs attention today?” is slow and easy to miss.

## 2. Solution

**AccountPulse** is a read-only Customer Success account-health agent. It gathers those signals, classifies risk, explains why, and recommends a next step for a human CSM. It does not act on the account.

Risk labels:

- **ACTION NEEDED** — intervene soon
- **WATCH** — monitor closely
- **HEALTHY** — no urgent action
- **NEEDS MANUAL REVIEW** — incomplete/untrusted data or ambiguous remediation

## 3. Tools (four sources)

| Tool | What it contributes |
|------|---------------------|
| `get_crm_account_data` | Owner, renewal, contract, CRM notes (mock + live HubSpot) |
| `get_product_usage` | Logins, trend, adoption, decline (mock) |
| `get_support_tickets` | Open tickets, severity, age, billing cues (mock) |
| `get_communication_activity` | Contact recency, sentiment, follow-up requests (mock) |

## 4. Deterministic flow (official demo)

```text
account_id
  → fetch CRM + usage + support + communications
  → rule-based classifier
  → five-section report
     1. ACTION NEEDED
     2. WATCH
     3. HEALTHY
     4. NEEDS MANUAL REVIEW
     5. SUMMARY FOR CSM
```

Official path uses rules in `analyze_account()` — not the small local LLM — so the Northwind demo is stable.

Primary command:

```bash
CRM_PROVIDER=mock python -c "from tools.report import analyze_account; print(analyze_account('acc_001'))"
```

Optional UI: `uv run streamlit run app.py`  
Optional LLM report: `REPORT_MODE=ollama` (not the official demo).

## 5. Live demo talking points (`acc_001` Northwind)

Show that Northwind appears **only** under ACTION NEEDED:

- Renewal pressure + budget notes
- High-severity billing ticket (TCK-4001)
- Contact gap / concerned sentiment
- Recommended next action pairs billing verification with owner sponsor check-in
- **Sources** list all four tools
- **WATCH** and **HEALTHY** are empty (`*(none)*`)
- **Human approval required: Yes**

Backup file: `northwind_report.txt` (also `presentation/evidence/northwind_report.txt`).

## 6. Safety restrictions

AccountPulse will **not**:

- send email/Slack
- update CRM records
- approve refunds or change entitlements from ticket text
- escalate or act without a human

Untrusted customer/ticket text is treated as evidence to review, not instructions to execute. Billing remediation stays in **NEEDS MANUAL REVIEW**.

## 7. Close

“MVP is complete: four sources, deterministic report, tests green, human-in-the-loop. Next: richer live product/support connectors and Pathfinder V2 follow-through.”

---

## Slide bullets (copy/paste)

1. **Problem:** Signal scatter → missed renewal risk  
2. **Solution:** Read-only CS health agent  
3. **Tools:** CRM · Usage · Support · Comms  
4. **Flow:** Fetch → classify → explain → recommend  
5. **Safety:** No writes; human approval required  
