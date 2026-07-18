# Phase 0 — Confirm V2 PRD in Pathfinder

## Goal

Confirm the AccountPulse **V2 PRD** remains submitted in Pathfinder before claiming PRD/process close-out.

## Why this is Phase 0

No code depends on Pathfinder, but the Eval Card / Agent Build submission is incomplete until the V2 PRD is verified present.

## Steps (Bath or Adedoyin)

1. Open Pathfinder (course / Agent Build portal used for this project).
2. Locate the **AccountPulse** agent / project.
3. Open the **V2 PRD** (or latest submitted PRD revision).
4. Confirm all of the following:
   - [ ] Submission status is **submitted** (not draft / withdrawn)
   - [ ] Title/name matches AccountPulse Customer Success Account Health Agent
   - [ ] Owners include **Bath Bilissalou** and **Adedoyin Ahoton**
   - [ ] Tools section lists CRM, support, product usage, and communication
   - [ ] Eval Card includes golden, edge, adversarial, and tool-failure cases
5. Record the result in [`evidence/pathfinder_v2_confirmation.md`](evidence/pathfinder_v2_confirmation.md).
6. If missing: resubmit from the local PRD PDF  
   `AccountPulse — Customer Success Agent PRD-2.pdf`  
   then re-run steps 1–5.

## Acceptance

Phase 0 is **Done** only when `evidence/pathfinder_v2_confirmation.md` has:

- `status: confirmed`
- a confirmation date
- confirmer name
- short note of what was seen (status + PRD title)

## Out of scope

- Editing the PRD content
- Live API connectors
- Eval fixture changes (Phase 1)
