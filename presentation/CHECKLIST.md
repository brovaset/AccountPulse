# Bath — presentation readiness checklist

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Stable deterministic mock demo (`acc_001`) | Done | Command below |
| 2 | Save complete Northwind report as backup | Done | `northwind_report.txt`, `evidence/northwind_report.txt` |
| 3 | Screenshots: tests passed, ACTION NEEDED, empty WATCH/HEALTHY, four sources | Done | `evidence/screenshots/` |
| 4 | Presentation explanation (problem, solution, tools, flow, safety) | Done | [`SCRIPT.md`](SCRIPT.md) |
| 5 | Confirm final V2 PRD remains submitted in Pathfinder | **Bath offline** | Open Pathfinder before the talk and confirm visually |

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

## Pathfinder (Bath only)

Before presenting, open Pathfinder and confirm the AccountPulse V2 PRD submission is still present. Mark row 5 Done only after that check.
