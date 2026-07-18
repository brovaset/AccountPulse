# Bath — presentation readiness checklist

## Phase 0 — Pathfinder (process)

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 0 | Confirm final V2 PRD remains submitted in Pathfinder | Done | [`PHASE0_PATHFINDER.md`](PHASE0_PATHFINDER.md), [`evidence/pathfinder_v2_confirmation.md`](evidence/pathfinder_v2_confirmation.md) |

## Phase 1 — Eval Card fidelity

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1.1 | Case 1 golden thresholds on `acc_001` | Done | usage ≥20% down, ticket ≥7d high-sev, contact ≥14d, renewal ≤60d |
| 1.2 | Case 1 next action: review ticket + check-in within 24h | Done | `_next_action` in report builder |
| 1.3 | Case 4 support failure → NEEDS MANUAL REVIEW | Done | `test_case4_support_failure_is_needs_manual_review` |
| 1.4 | Case 3 adversarial CRM note ignored | Done | `test_case3_adversarial_crm_note_ignored_flags_on_usage_and_renewal` |

## Phase 2 — Morning briefing (feature)

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 2 | Multi-account prioritized morning briefing | Done | `analyze_portfolio`, `python agent.py --briefing`, Streamlit button |

## Phase 3 — Live connectors (feature)

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 3.1 | Zendesk support | Done | `tools/support/zendesk_client.py`, `SUPPORT_PROVIDER` |
| 3.2 | Product usage live path | Done | **PostHog (free)** `tools/usage/posthog_client.py`; Gainsight kept optional |
| 3.3 | Gmail communications | Done (code) / setup pending token | `gmail_client.py` + `scripts/gmail_oauth_setup.py` |
| 3.4 | Salesforce CRM | Deferred | Wait — HubSpot remains the live CRM path |

## Presentation pack

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Stable deterministic mock demo (`acc_001`) | Done | Command below |
| 2 | Save complete Northwind report as backup | Done | `northwind_report.txt`, `evidence/northwind_report.txt` |
| 3 | Screenshots: tests passed, ACTION NEEDED, empty WATCH/HEALTHY, four sources | Done | `evidence/screenshots/` |
| 4 | Presentation explanation (problem, solution, tools, flow, safety) | Done | [`SCRIPT.md`](SCRIPT.md) |

## Screenshots map

| File | Shows |
|------|--------|
| `01_tests_and_report.png` | Full evidence page: 44 tests + full report |
| `04_tests_passed.png` | Tests band only |
| `05_report_sections.png` | Report body (ACTION NEEDED → SUMMARY) |
| `06_risk_badge_action_needed.png` | Streamlit ACTION NEEDED section |
| `07_sources_four_and_watch_empty.png` | Four sources + empty WATCH |
| `08_watch_healthy_empty.png` | Empty WATCH + HEALTHY |

## Primary demo

```bash
CRM_PROVIDER=mock python -c "from tools.report import analyze_account; print(analyze_account('acc_001'))"
```

## Backup report

```bash
CRM_PROVIDER=mock python -c "from tools.report import analyze_account; print(analyze_account('acc_001'))" > northwind_report.txt
```

## Tests

```bash
uv run pytest
# Current suite: 44 passed (original plan cited 42)
```

## Pathfinder (Phase 0)

Done — `evidence/pathfinder_v2_confirmation.md` recorded `status: confirmed` on 2026-07-18.
