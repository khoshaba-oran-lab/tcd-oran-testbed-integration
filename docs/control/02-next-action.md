# Next authorised action

- UPDATED_UTC=2026-09-13T18:50:42Z
- LAST_COMPLETED_ACTION=RECOVERY.R3.CLOSE-FAIL
- LAST_ACTION_RESULT=PASS
- CURRENT_STAGE=R3_REMEDIATION
- CURRENT_ACTION=NONE
- NEXT_AUTHORISED_ACTION=NONE
- NEXT_PLANNED_ACTION=RECOVERY.R3.REMEDIATION-PLAN
- PURPOSE=design a bounded user-plane readiness remediation before any new lifecycle session

## Current blocker

- R3 acceptance is closed with failure at `USER_PLANE_READINESS_GATE`.
- Required fresh evidence `/tmp/sci-oran/user-plane-smoke/latest.env` was absent.
- Tb3 is stopped and the single R3 lifecycle session has been consumed.

## Restrictions

- Do not replay the successful R3 deploy.
- Do not start another lifecycle session without separate authorisation.
- Do not execute automatic recover or reset.
- Do not advance to R4.
- Do not issue scientific PRB control.
- Never replay the consumed T2 R03 trigger.
