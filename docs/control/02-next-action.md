# Next authorised action

- UPDATED_UTC=2026-09-13T19:59:47Z
- LAST_COMPLETED_ACTION=RECOVERY.R4.CLOSE-BY-PROVENANCE
- LAST_ACTION_RESULT=PASS
- CURRENT_STAGE=R5
- CURRENT_ACTION=NONE
- NEXT_AUTHORISED_ACTION=NONE
- NEXT_PLANNED_ACTION=RECOVERY.R5.1
- PURPOSE=restore T2 readiness without executing the scientific T2 trigger

## R4 closure

- R4 qualification method: provenance plus safe regression.
- T1 golden provenance: `PASS`.
- Transaction-validator provenance: `PASS`.
- T2 no-control evidence: `5_OF_5 PASS`.
- Fail-closed regression: `PASS`.
- Duration-limit contract: `PASS`.
- Scientific trigger attempts: `0`.

## R5 authorisation boundary

- R5 contains runtime operations and requires explicit user authorisation.
- Tb3 currently remains stopped.
- Do not start, deploy, recover or reset Tb3 without that authorisation.
- Do not issue the T2 PRB trigger.
- Never replay the consumed T2 R03 trigger.
