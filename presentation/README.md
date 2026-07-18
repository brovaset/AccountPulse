# Presentation pack (Bath)

Artifacts for the AccountPulse MVP demo.

| File | Purpose |
|------|---------|
| [`SCRIPT.md`](SCRIPT.md) | 5-minute talk track: problem, solution, tools, flow, safety |
| [`CHECKLIST.md`](CHECKLIST.md) | Bath readiness checklist + Pathfinder offline item |
| [`evidence/northwind_report.txt`](evidence/northwind_report.txt) | Backup deterministic report for `acc_001` |
| [`evidence/pytest_results.txt`](evidence/pytest_results.txt) | Latest pytest pass log (44 passed) |
| [`evidence/screenshots/`](evidence/screenshots/) | Visual evidence for tests + report sections |
| [`../northwind_report.txt`](../northwind_report.txt) | Same backup at repo root (plan command path) |

## Demo (official)

```bash
CRM_PROVIDER=mock python -c "from tools.report import analyze_account; print(analyze_account('acc_001'))"
```

UI (optional): `CRM_PROVIDER=mock uv run streamlit run app.py`
