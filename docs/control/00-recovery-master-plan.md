# Sci-O-RAN recovery and experiment resumption plan

## Canonical sources

- Master plan: `docs/control/00-recovery-master-plan.md`
- Current state: `docs/control/01-current-state.md`
- Next action: `docs/control/02-next-action.md`
- Scientific design: `docs/12-siso-system-identification-design.md`
- T2 protocol: `docs/12-t2-26to39-scientific-protocol.md`

## Canonical scientific state

- T1 is closed and validated; its accepted evidence is the golden dataset.
- T2 is scientifically incomplete with one valid repetition, R03.
- The R03 scientific trigger is consumed and must never be replayed.
- R01V5 is an aborted pretrigger attempt and consumed no scientific trigger.
- No new T2 trigger and no T3-T6 transition is currently authorised.

## Stage R0 - Freeze and establish truth

Status: COMPLETE.

Experiments and runtime mutations are paused. Repository, branch, runtime,
T1 and T2 evidence boundaries have been established and published.

## Stage R1 - Repository and lifecycle consolidation

Status: COMPLETE after `RECOVERY.R1.CLOSE` passes.

The lifecycle source is integrated under `sci-oran/ansible`. Controller
paths are portable, the real inventory remains untracked, and execution
remains prohibited until controller qualification.

## Stage R2 - External controller qualification

Status: COMPLETE.


Qualification was closed by `RECOVERY.R2.CLOSE`. The active controller is
`coll.vntu.org`; it uses the canonical Git working copy and a controller-local,
Git-ignored inventory. SSH target identity and all 13 playbook syntax checks
passed. No lifecycle playbook was executed during qualification.


Confirm the controller host, repository, Ansible installation, local
inventory, SSH target and native syntax checks. This stage is read-only.

## Stage R3 - Tb3 lifecycle acceptance

Status: COMPLETE under the amended lifecycle-only acceptance contract.

The original strict acceptance attempt remains recorded as FAIL because the
comprehensive doctor failed at `USER_PLANE_READINESS_GATE`. That historical
result is not rewritten.

The amended R3 contract accepts the lifecycle mechanism using its existing
lifecycle preflight, controlled deploy, runtime container/network status,
evidence manifests, controlled stop and post-stop verification. All of these
gates passed during the single authorised lifecycle session.

Comprehensive experiment readiness, including fresh functional user-plane
evidence and readiness-artifact freshness, is evaluated in R5. No doctor code
or scientific criterion is weakened.

Perform one controlled preflight, start, status, doctor and stop cycle.
Do not automatically recover or repeat an unknown failure.

## Stage R4 - Offline experiment qualification

Status: INCOMPLETE - DURATION LIMIT FAILED.

Reuse the accepted T1 evidence, existing transaction validator and runner.
When accepted evidence and relevant sources have not drifted, qualification is
provenance-based rather than a repetition of the scientific experiment.
Safe regression tests may be rerun only when they cannot contact live runtime.

R4 acceptance requires T1 golden provenance, transaction-validator provenance,
five accepted T2 no-control trials, fail-closed regression and a bounded
execution-duration contract. No scientific trigger is permitted.

Duration-limit adjudication supersedes the premature R4 completion
decision. Receiver-readiness timeout and precontrol sample-age bounds do not
constitute a global experiment-duration limit. The protocol defines minimum
pre/post observations and five-second extensions, but no maximum total
duration or maximum extension count. The first four R4 criteria remain
accepted; R5 is prohibited until this R4 blocker is resolved.

## Stage R5 - Restore T2 readiness

Status: NOT STARTED.

The comprehensive `scripts/sci-oran-doctor.sh` contract belongs to this
stage. R5 requires fresh user-plane smoke evidence, readiness-artifact
freshness and `SCI_ORAN_READY_GATE=PASS` for the same runtime incarnation.

Require platform health, user-plane smoke, telemetry, actuator path,
prospective 26-PRB readback and pre-step stationarity. No T2 trigger.

## Stage R6 - Complete T2

Status: NOT AUTHORISED.

Use a fresh transaction and run ID. Never replay R03. Permit one new
26-to-39 trigger only after every R5 gate passes.

## Stage R7 - Execute T3 through T6

Status: NOT AUTHORISED.

Use one parameterised pipeline and accept each transition separately.

## Stage R8 - Final modelling and shadow predictor

Status: NOT STARTED.

Compare models, saturation and hysteresis before qualifying ARX as a
shadow predictor. Closed-loop control requires a later decision.

## Anti-loop execution policy

- Read-only checks may be grouped into one bounded action.
- Repository changes use one checkpoint per logical result.
- Runtime and scientific actuation remain strictly one-action.
- A stage normally permits two actions and at most one repair.
- Confirmed evidence is not re-audited unless its provenance changes.
- Full logs go to evidence; chat output remains bounded.
- Only the three control documents above govern execution state.

## R4 bounded-duration design adjudication

The missing experiment-duration contract is now designed but not yet
implemented. The frozen policy permits at most two 5-second stationarity
extensions. This bounds initial pre-step observation at 21 seconds and every
post-step observation at 20 seconds.

For six transitions, the maximum observation budget is:

`21 + 6 * 20 = 141 seconds`.

The end-to-end wall-clock ceiling is 180 seconds. The remaining 39 seconds are
a bounded operational allowance for traffic startup, six exactly-once
actuation/readback transactions and final evidence completion.

A phase or global timeout is fail-closed. It must prohibit the next trigger and
must never cause automatic replay of a trigger already attempted.


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

## R4 bounded-duration supervisor implementation

The frozen duration contract now has a dedicated executable supervisor.
It owns the initial and six post-transition observation deadlines, the
extension count, the global wall-clock deadline and exactly-once trigger
ordering. Live mode requires both an enable environment value and an explicit
authorization token.

Nine offline tests verify arithmetic, no-control behaviour, dual live
authorization, phase/global fail-closed limits, six exactly-once trigger
attempts and prohibition of later triggers after an ambiguous or failed
trigger.

The supervisor is not yet bound to a concrete live T2 command plan. Therefore
R4 remains incomplete and R5 remains unauthorized.

R4_DURATION_SUPERVISOR_IMPLEMENTATION_V1_BEGIN
R4_DURATION_SUPERVISOR_IMPLEMENTATION=PASS
SUPERVISOR_SHA256=dc12b93b24f67dfe2d2163d1c6c545269f5efcc63d688f70ef56c1b15f6d5633
SUPERVISOR_TEST_SHA256=f21c3584c733d3a12948808a55ea8b11d7debedd25a9ea2eca777a25cde67514
OFFLINE_TESTS=9_OF_9_PASS
PRE_STEP_MAXIMUM_DURATION_S=21
POST_STEP_MAXIMUM_DURATION_S=20
MAX_STATIONARITY_EXTENSIONS=2
OBSERVATION_BUDGET_MAXIMUM_S=141
EXPERIMENT_MAXIMUM_DURATION_S=180
LIVE_DEFAULT_GATE=FAIL_CLOSED
AUTOMATIC_TRIGGER_REPLAY=PROHIBITED
LIVE_MODE_EXECUTED=NO
EVIDENCE_DIR=/home/khoshaba/sci-oran/staging/r4-duration-supervisor/r4-supervisor-20260914T063504Z-b34210ca
R4_DURATION_SUPERVISOR_IMPLEMENTATION_V1_END
