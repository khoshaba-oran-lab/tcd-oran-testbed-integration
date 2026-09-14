# Next authorised action

- UPDATED_UTC=2026-09-13T20:17:43Z
- LAST_COMPLETED_ACTION=RECOVERY.R4.RECORD-ER-LIMIT-FAIL
- LAST_ACTION_RESULT=PASS
- CURRENT_STAGE=R4_DURATION_CONTRACT
- CURRENT_ACTION=NONE
- NEXT_AUTHORISED_ACTION=NONE
- NEXT_PLANNED_ACTION=RECOVERY.R4.DURATION-CONTRACT-DESIGN
- PURPOSE=define scientifically justified finite experiment-duration bounds before implementation

## R4 state

- Four of five R4 criteria are accepted.
- `ER_LIMIT_CONTRACT=FAIL`.
- The previous R4 COMPLETE decision is superseded.
- No existing accepted evidence is invalidated.
- Tb3 remains stopped.

## Missing contract values

- `PRE_STEP_MAXIMUM_DURATION_S`
- `POST_STEP_MAXIMUM_DURATION_S`
- `MAX_STATIONARITY_EXTENSIONS`
- `EXPERIMENT_MAXIMUM_DURATION_S`

## Restrictions

- Do not rerun T1 evidence checks.
- Do not repeat the five T2 no-control trials.
- Do not create another R4 discovery action.
- Do not modify runner or protocol before contract design is accepted.
- Do not start, deploy, recover or reset Tb3.
- Do not advance to R5.
- Do not issue scientific PRB control.

## Current authorised boundary after duration design

The design decision is complete. No implementation is authorised by this
checkpoint.

The next planned action is one bounded source-code action that implements the
frozen limits without changing scientific thresholds, PRB transitions, model
parameters or user-plane readiness policy.


R4_DURATION_CONTRACT_DESIGN_V1_BEGIN
R4_DURATION_CONTRACT_DESIGN=PASS
STARTUP_GUARD_MINIMUM_S=1
PRE_STEP_MINIMUM_DURATION_S=11
POST_STEP_MINIMUM_DURATION_S=10
POST_STEP_EXTENSION_S=5
MAX_STATIONARITY_EXTENSIONS=2
PRE_STEP_MAXIMUM_DURATION_S=21
POST_STEP_MAXIMUM_DURATION_S=20
OBSERVATION_BUDGET_MAXIMUM_S=141
EXPERIMENT_MAXIMUM_DURATION_S=180
EXPERIMENT_TIMEOUT_SCOPE=TRAFFIC_START_THROUGH_POST_T6_FINALIZATION
STATIONARITY_TIMEOUT_RESULT=FAIL_CLOSED
NEXT_TRIGGER_AFTER_TIMEOUT=PROHIBITED
AUTOMATIC_TRIGGER_REPLAY=PROHIBITED
EXISTING_TRIGGER_STATE_MUST_BE_REPORTED=YES
R4_DURATION_CONTRACT_DESIGN_V1_END

NEXT_AUTHORISED_ACTION=NONE
NEXT_PLANNED_ACTION=RECOVERY.R4.DURATION-CONTRACT-IMPLEMENT
