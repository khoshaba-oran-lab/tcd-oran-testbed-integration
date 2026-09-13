# Next authorised action

- UPDATED_UTC=2026-09-13T15:39:53Z
- LAST_COMPLETED_ACTION=RECOVERY.R1.CLOSE
- LAST_ACTION_RESULT=PASS
- CURRENT_STAGE=R2
- CURRENT_ACTION=NONE
- NEXT_AUTHORISED_ACTION=RECOVERY.R2.1
- PURPOSE=qualify the external Ansible controller and its inventory read-only

## Restrictions

- Do not execute lifecycle playbooks in normal mode.
- Do not create or modify the real inventory automatically.
- Do not start or redeploy Tb3.
- Do not issue scientific PRB control.
- Never replay the consumed T2 R03 trigger.
