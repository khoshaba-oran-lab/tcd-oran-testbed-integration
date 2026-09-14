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

## R4 scope adjudication

R4 is conclusively scoped as offline experiment-tool qualification. Its
accepted evidence consists of checksum-valid T1 provenance, transaction
validator provenance, five no-control T2 trials, fail-closed regression and
the offline-tested bounded-duration supervisor.

Binding that supervisor to a concrete live T1--T6 sequence is not evidence
required to close offline R4. It is deferred to scientific-run preparation.

This deferral does not authorise an unbounded experiment. Before any future
scientific trigger, a concrete duration-supervisor binding must independently
pass. Missing or failed binding prohibits traffic/control admission.

R5 remains the comprehensive platform and user-plane readiness stage.

R4_SCOPE_ADJUDICATION_V1_BEGIN
R4_SCOPE_ADJUDICATION=PASS
R4_SCOPE=OFFLINE_EXPERIMENT_TOOL_QUALIFICATION
R4_STATUS=COMPLETE_OFFLINE
R4_OFFLINE_ACCEPTANCE=PASS
T1_GOLDEN_PROVENANCE=PASS
TRANSACTION_VALIDATOR_PROVENANCE=PASS
T2_DRY_RUN_NO_TRIGGER=PASS
FAIL_CLOSED_CONTRACT=PASS
ER_LIMIT_OFFLINE_CONTRACT=PASS
OFFLINE_SUPERVISOR_TESTS=9_OF_9_PASS
SUPERVISOR_SHA256=dc12b93b24f67dfe2d2163d1c6c545269f5efcc63d688f70ef56c1b15f6d5633
SUPERVISOR_TEST_SHA256=f21c3584c733d3a12948808a55ea8b11d7debedd25a9ea2eca777a25cde67514
R4_EVIDENCE_MANIFEST=/home/khoshaba/sci-oran/staging/r4-duration-supervisor/r4-supervisor-20260914T063504Z-b34210ca/SHA256SUMS
LIVE_DURATION_SEQUENCE_BINDING=DEFERRED_REQUIRED
LIVE_DURATION_SEQUENCE_BINDING_GATE=NOT_EXECUTED
LIVE_BINDING_IS_NOT_R4_PASS_EVIDENCE=YES
LIVE_BINDING_REQUIRED_BEFORE_ANY_SCIENTIFIC_TRIGGER=YES
SCIENTIFIC_TRIGGER_ADMISSION=BLOCKED
AUTOMATIC_TRIGGER_REPLAY=PROHIBITED
R5_STATUS=NOT_STARTED
R5_AUTHORISED=NO
TB3_RUNTIME=STOPPED
R4_SCOPE_ADJUDICATION_V1_END

## R5 readiness qualification plan

R5 restores current Tb3 readiness without executing the scientific T2 trigger. The early check is the lifecycle/platform subset. The comprehensive Doctor runs only after the active policy smoke has created fresh user-plane evidence.

A PRB correction, if required, is a separate exactly-once infrastructure action. Live duration-supervisor binding remains mandatory before any future scientific trigger.

R5_READINESS_PLAN_V1_BEGIN
R5_PLAN_FROZEN_UTC=2026-09-14T08:30:56Z
R5_PLAN_STATUS=FROZEN
R5_STATUS=NOT_STARTED
R5_PURPOSE=RESTORE_TB3_READINESS_FOR_T2_WITHOUT_T2_TRIGGER
R5_STEP_01=CONTROLLED_DEPLOY_WITH_CONFIRM
R5_STEP_02=LIFECYCLE_PLATFORM_SUBSET_STATUS
R5_STEP_03=UE_REGISTRATION_TUN_PDU_ADDRESS_AND_ROUTE
R5_STEP_04=POLICY_USER_PLANE_SMOKE_CREATE_FRESH_LATEST_ENV
R5_STEP_05=COMPREHENSIVE_DOCTOR_WITHIN_300_SECONDS
R5_STEP_06=SEPARATE_DL_UL_FUNCTIONAL_SMOKE
R5_STEP_07=TELEMETRY_READINESS
R5_STEP_08=READ_ONLY_ACTUATOR_PATH_AND_PROSPECTIVE_READBACK
R5_STEP_09=INITIAL_PRB_26_VERIFICATION
R5_STEP_10=OPTIONAL_SEPARATE_EXACTLY_ONCE_RESET_TO_26
R5_STEP_11=SUSTAINED_UDP_DL_WITH_TELEMETRY
R5_STEP_12=PRE_STEP_OUTPUT_STATIONARITY
R5_STEP_13=T2_TRIGGER_REMAINS_NOT_EXECUTED
EARLY_PLATFORM_CHECK=LIFECYCLE_PLATFORM_SUBSET_ONLY
COMPREHENSIVE_DOCTOR_POSITION=AFTER_POLICY_USER_PLANE_SMOKE
SMOKE_EVIDENCE_PRODUCER=scripts/sci-oran-user-plane-smoke.sh
SMOKE_EVIDENCE_PATH=/tmp/sci-oran/user-plane-smoke/latest.env
SMOKE_TO_DOCTOR_MAX_SECONDS=300
POLICY_SMOKE_PROVES=ICMP_ROUTE_TUN_COUNTERS_AND_PROCESS_CONTINUITY
POLICY_SMOKE_IS_SUSTAINED_DL_UL_PROOF=NO
ACTUATOR_PATH_CHECK_ALLOWS_PRB_WRITE=NO
RESET_TO_26_SEPARATE_EXACTLY_ONCE_ACTION=YES
RESET_TO_26_MAY_BE_MIXED_WITH_T2_TRIGGER=NO
AUTOMATIC_TRIGGER_REPLAY=PROHIBITED
FAIL_REQUIRES_SEPARATE_CONTROLLED_STOP=YES
PASS_WITHOUT_IMMEDIATE_AUTHORISED_CONTINUATION_REQUIRES_CONTROLLED_STOP=YES
LIVE_DURATION_SEQUENCE_BINDING=DEFERRED_REQUIRED
LIVE_BINDING_REQUIRED_BEFORE_ANY_SCIENTIFIC_TRIGGER=YES
MANDATORY_PRE_TRIGGER_ACTION=RECOVERY.SCIENTIFIC-RUN.DURATION-SUPERVISOR-BIND
SCIENTIFIC_TRIGGER_ADMISSION=BLOCKED
R5_PASS_REQUIRES_PLATFORM_HEALTH=PASS
R5_PASS_REQUIRES_USER_PLANE=PASS
R5_PASS_REQUIRES_TELEMETRY=PASS
R5_PASS_REQUIRES_ACTUATOR_PATH=PASS
R5_PASS_REQUIRES_INITIAL_PRB_26=PASS
R5_PASS_REQUIRES_PRE_STATIONARITY=PASS
R5_PASS_REQUIRES_T2_TRIGGER_EXECUTED=NO
R5_RUNTIME_ACTION_AUTHORISED=NO
NEXT_AUTHORISED_ACTION=NONE
NEXT_PLANNED_ACTION=RECOVERY.R5.2.CONTROLLED-DEPLOY-RETRY
R5_READINESS_PLAN_V1_END
## R5 deploy and platform-status checkpoint

The resumed controlled deployment and bounded direct read-only platform
status passed. The malformed first status wrapper is retained only as
non-authoritative diagnostic provenance. The successful bounded retry is
the authoritative platform-status evidence.

R5_PLATFORM_STATUS_CHECKPOINT_V1_BEGIN
CHECKPOINT_UTC=2026-09-14T14:42:50Z
ACTION_RESULT=PASS
R5_STATUS=IN_PROGRESS
R5_PLAN_STATUS=FROZEN
R5_COMPLETED_STEP_01=CONTROLLED_DEPLOY_WITH_CONFIRM
R5_COMPLETED_STEP_02=LIFECYCLE_PLATFORM_SUBSET_STATUS
DEPLOY_OPERATION_ID=lifecycle-deploy-20260914T140029Z-107030a7
DEPLOY_GATE=PASS
DEPLOY_LOG=/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs/r5-resume-deploy-20260914T140028Z.log
DEPLOY_LOG_SHA256=e42ec5e2e35f82bf5ff9a3c3a3ec7175075dcf9cacc3f40ba195f31c96a54def
FAILED_STATUS_LOG_ROLE=NON_AUTHORITATIVE_WRAPPER_DIAGNOSTIC
FAILED_STATUS_LOG=/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs/r5-direct-readonly-status-20260914T142548Z.log
FAILED_STATUS_LOG_SHA256=ffd1932f64ab413f0b14df3a10e7366ed82dbd8ed6c74b834cdf3ec6159315b1
FAILED_STATUS_LOG_USED_FOR_PLATFORM_DECISION=NO
DIRECT_READONLY_STATUS_RETRY=PASS
AUTHORITATIVE_PLATFORM_STATUS_SOURCE=/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs/r5-direct-readonly-status-retry-20260914T143051Z.log
STATUS_LOG=/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs/r5-direct-readonly-status-retry-20260914T143051Z.log
STATUS_LOG_SHA256=9624a8ed5533440cbdfee99145c90602aabf7ebc127cad3520c84372793c11d1
STATUS_TIMEOUT_SECONDS=30
TARGET_HOSTNAME=tb3-dell
EXPECTED_CONTAINER_COUNT=4
RUNNING_CONTAINER_COUNT=4
ZERO_RESTART_CONTAINER_COUNT=4
CONTAINER_RUNNING_GATE=PASS
CONTAINER_RESTART_COUNT_GATE=PASS
NETWORK=tcd-base05-zmq_ran
NETWORK_MEMBER_COUNT=4
NETWORK_MEMBERSHIP_GATE=PASS
PLATFORM_STATUS_GATE=PASS
TB3_RUNTIME=RUNNING
TB3_RUNTIME_CHANGED_BY_STATUS=NO
USER_PLANE_SMOKE_EXECUTED=NO
DOCTOR_EXECUTED=NO
PRB_CONTROL_EXECUTED=NO
SCIENTIFIC_CONTROL_EXECUTED=NO
T2_TRIGGER_EXECUTED=NO
NEXT_AUTHORISED_ACTION=RECOVERY.R5.4.UE-SESSION-READINESS
R5_PLATFORM_STATUS_CHECKPOINT_V1_END
## R5 UE session readiness checkpoint

The bounded read-only UE inspection passed. The UE process remained running,
the PDU session was established, and the expected interface, address and route
were present. No active user-plane probe was executed.

R5_UE_SESSION_CHECKPOINT_V1_BEGIN
CHECKPOINT_UTC=2026-09-14T14:50:43Z
ACTION_RESULT=PASS
R5_STATUS=IN_PROGRESS
R5_COMPLETED_STEP_03=UE_REGISTRATION_TUN_PDU_ADDRESS_AND_ROUTE
UE_CONTAINER=base05_srsran_srsue
UE_CONTAINER_STATUS=running
UE_CONTAINER_RESTART_COUNT=0
UE_PROCESS_CONTINUITY_GATE=PASS
UE_REGISTRATION_EVIDENCE=PDU_SESSION_ESTABLISHMENT_SUCCESSFUL
UE_REGISTRATION_GATE=PASS
EXPECTED_UE_INTERFACE=tun_srsue
UE_USER_PLANE_INTERFACE_GATE=PASS
EXPECTED_UE_PDU_IPV4=10.45.1.2
UE_PDU_IPV4_GATE=PASS
EXPECTED_UPF_IPV4=10.45.1.1
UE_TO_UPF_ROUTE_GATE=PASS
UE_SESSION_READINESS_GATE=PASS
UE_READINESS_LOG=/home/khoshaba/sci-oran/staging/r5-readiness/controller-logs/r5-ue-session-readiness-20260914T144634Z.log
UE_READINESS_LOG_SHA256=79853833ec31688cf9439f0d1d5063dcae7546cfcd262b969f91233fc72809ed
TB3_RUNTIME=RUNNING
TB3_RUNTIME_CHANGED=NO
ACTIVE_USER_PLANE_PROBE_EXECUTED=NO
USER_PLANE_TRAFFIC_EXECUTED=NO
USER_PLANE_SMOKE_EXECUTED=NO
SMOKE_EVIDENCE_CREATED=NO
SMOKE_EVIDENCE_FRESHNESS_WINDOW_STARTED=NO
DOCTOR_EXECUTED=NO
PRB_CONTROL_EXECUTED=NO
SCIENTIFIC_CONTROL_EXECUTED=NO
T2_TRIGGER_EXECUTED=NO
NEXT_AUTHORISED_ACTION=RECOVERY.R5.5.POLICY-USER-PLANE-SMOKE
R5_UE_SESSION_CHECKPOINT_V1_END
