# Next authorised action

- UPDATED_UTC=2026-09-13T17:55:11Z
- LAST_COMPLETED_ACTION=RECOVERY.R2.CLOSE
- LAST_ACTION_RESULT=PASS
- CURRENT_STAGE=R3
- CURRENT_ACTION=NONE
- NEXT_AUTHORISED_ACTION=NONE
- NEXT_PLANNED_ACTION=RECOVERY.R3.1
- PURPOSE=await explicit authorisation for one controlled Tb3 lifecycle acceptance session

## Restrictions

- Do not start, deploy, stop, recover or reset Tb3 without explicit R3 authorisation.
- Do not delete the preserved legacy local branch or old inventory.
- Do not modify the real inventory automatically.
- Do not issue scientific PRB control.
- Never replay the consumed T2 R03 trigger.
