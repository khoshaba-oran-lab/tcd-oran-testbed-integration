# R6-J admission dependency-order correction

UTC decision date: 2026-10-03

R6J_ADMISSION_ORDER_CORRECTION_VERSION=1
R6J_ADMISSION_ORDER_CORRECTION_STATUS=APPROVED
R6J_ADMISSION_ORDER_CORRECTION_REASON=GENERIC_PREFLIGHT_DOCTOR_REQUIRES_FRESH_USER_PLANE_SMOKE_EVIDENCE

## Problem

The original R6-J staged admission sequence placed the canonical generic
experiment preflight before Prompt-12-specific user-plane readiness.

Live R6-J qualification established that this ordering is not executable.

The canonical generic pre-workload path is:

    scripts/experiment-harness/run-experiment.sh
        -> sci_oran_precheck
        -> scripts/sci-oran-doctor.sh
        -> scripts/experiment-harness/r6-f-portable-runtime-preflight.py

The doctor is strict read-only. Its user-plane policy requires fresh active
user-plane smoke evidence at:

    /tmp/sci-oran/user-plane-smoke/latest.env

The required smoke evidence must:

- exist;
- contain the required smoke gates;
- be no older than the configured freshness limit;
- match the current UE, gNB and 5GC runtime fingerprints;
- match the current runtime image identities.

During R6-J Gate-03 qualification on 2026-10-03, the smoke-evidence root and
latest.env were absent. The doctor therefore returned:

    USER_PLANE_EVIDENCE_FILE_GATE=FAIL
    USER_PLANE_READINESS_GATE=FAIL
    SCI_ORAN_READY_GATE=FAIL
    FAILURE_REASON=USER_PLANE_READINESS_GATE

The canonical generic preflight correctly propagated this failure.

## Architectural constraint

The R6-H architecture remains valid and is not superseded by this decision.

Generic preflight remains read-only and fail-closed.

Generic preflight must not:

- execute user-plane smoke;
- generate ping or iperf traffic;
- perform Prompt-12 precontrol;
- control PRBs;
- execute a Prompt-12 scientific trigger;
- perform lifecycle mutation;
- perform Docker mutation.

Active user-plane evidence production remains outside generic preflight and is
owned by:

    scripts/sci-oran-user-plane-smoke.sh

Therefore active evidence production must precede any generic preflight whose
doctor contract requires that evidence.

## Corrected R6-J staged admission order

R6J_STAGE_01=AUTHORITATIVE_REPOSITORY_CONVERGENCE
R6J_STAGE_02=CANONICAL_LIFECYCLE_DAY_START
R6J_STAGE_03A=ACTIVE_USER_PLANE_EVIDENCE_PRODUCTION
R6J_STAGE_03B=CANONICAL_GENERIC_EXPERIMENT_PREFLIGHT
R6J_STAGE_04=PROMPT12_SPECIFIC_PRECONTROL_READINESS
R6J_STAGE_05=PROSPECTIVE_INITIAL_PRB_APPLIED_READBACK
R6J_STAGE_06=SEPARATE_EXACTLY_ONCE_T2_SCIENTIFIC_AUTHORIZATION

The ordering dependency is:

    Stage 02
      -> Stage 03A
      -> Stage 03B
      -> Stage 04
      -> Stage 05
      -> Stage 06

Stage 03A is a bounded diagnostic action, not a Prompt-12 scientific
experiment. It may emit only the active diagnostic traffic authorised by the
user-plane readiness policy. At the time of this decision that policy specifies
three ICMP packets.

Stage 03A requires separate explicit authorisation because it generates active
diagnostic traffic and writes fresh runtime evidence.

Stage 03B may execute only after Stage 03A has passed and produced fresh
runtime-matching evidence.

Stage 04 now means Prompt-12-specific precontrol readiness only. Active
user-plane smoke is no longer grouped into Stage 04 because that evidence is a
dependency of Stage 03B.

Stage 05 remains readback-only unless a separate control mutation is explicitly
authorised.

Stage 06 remains the separate exactly-once authorisation boundary for the T2
26-to-39 PRB scientific transition.

## Current status at this decision

R6J_STAGE_01_STATUS=PASS
R6J_STAGE_02_STATUS=PASS
R6J_STAGE_03A_STATUS=NOT_EXECUTED
R6J_STAGE_03B_STATUS=BLOCKED_BY_STAGE_03A
R6J_STAGE_04_STATUS=NOT_EXECUTED
R6J_STAGE_05_STATUS=NOT_EXECUTED
R6J_STAGE_06_STATUS=NOT_EXECUTED

R6J_NEXT_REQUIRED_STAGE=ACTIVE_USER_PLANE_EVIDENCE_PRODUCTION

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO

No existing scientific trigger is authorised or consumed by this architectural
correction.
