# Prompt 12 Doctor Repository Readiness Repair

## Status

Doctor repository-readiness repair: VALIDATED.

Baseline repository HEAD before repair:

    08b11e03ce4683f368651f826c8879ff9a483d66

Prompt-12 branch:

    feat/prompt12-siso-identification

Repository readiness profile:

    prompt12-siso-identification

Repository readiness policy version:

    2

## Original failure

The healthy Prompt-12 runtime passed the functional readiness gates, including
host, container, network, ZMQ, N2, E2, E2SM-RC, UE session, user-plane,
traffic-harness, and process-continuity checks.

The overall Doctor nevertheless returned:

    REPOSITORY_BRANCH_GATE=FAIL
    REPOSITORY_REPRODUCIBILITY_GATE=FAIL
    SCI_ORAN_READY_GATE=FAIL

The runtime was not the root cause.

## Proven root causes

Three repository-contract defects were established.

1. The repository policy still expected the legacy Prompt-11B branch:

       feat/tb3-dell-reproducibility

2. The Doctor engine contained stage-specific Prompt-11B assumptions,
   including the literal legacy branch and PROMPT11B-specific policy keys.

3. The old repository contract covered zero of the eleven files introduced
   specifically for Prompt-12 SISO identification.

A fourth residual hard-code was found during repair validation:

    REPOSITORY_BASH_SCRIPT_COUNT == 4

This fixed cardinality was removed rather than changed to another
stage-specific number.

## Architectural repair

The Doctor is now treated as a generic fail-closed readiness engine.

Stage-specific repository identity is owned by:

    deploy/phase-2-flexric/tb3-runtime/locks/repository-readiness.policy

The policy now declares:

    REPOSITORY_READINESS_POLICY_VERSION=2
    REPOSITORY_PROFILE=prompt12-siso-identification
    EXPECTED_BRANCH=feat/prompt12-siso-identification
    TRACKED_DEPENDENCY_COUNT=20
    DEVELOPMENT_FILE_COUNT=5

The twenty mandatory tracked dependencies consist of:

- nine pre-existing baseline/runtime dependencies;
- eleven Prompt-12 SISO identification artifacts.

The Doctor itself contains neither the Prompt-11B branch nor the Prompt-12
branch as a literal repository requirement.

## Future Prompt transition rule

When moving from Prompt 12 to Prompt 13 or a later experimental stage:

1. do not rewrite Doctor merely because the Prompt number changed;
2. define the new stage in repository-readiness.policy;
3. update REPOSITORY_PROFILE;
4. update EXPECTED_BRANCH;
5. explicitly update the required dependency set;
6. run a positive repository-contract test;
7. run a negative wrong-branch test;
8. run a negative dirty-required-file test;
9. run the live Doctor;
10. checkpoint only after all fail-closed tests pass.

The invariant is:

    Doctor = generic validation engine
    policy = stage-specific reproducibility contract

## Fail-closed validation

Validated on 2026-08-21.

Positive contract:

    REPOSITORY_POLICY_GATE=PASS
    REPOSITORY_POLICY_CONTRACT_GATE=PASS
    REPOSITORY_BRANCH_GATE=PASS
    REPOSITORY_TRACKED_DEPENDENCIES_GATE=PASS
    REPOSITORY_REPRODUCIBILITY_GATE=PASS

Negative wrong-branch test:

    REPOSITORY_BRANCH_GATE=FAIL
    REPOSITORY_REPRODUCIBILITY_GATE=FAIL
    SCI_ORAN_READY_GATE=FAIL
    exit_code=20

Negative dirty Prompt-12 dependency test:

    dirty_file=docs/12-siso-system-identification-design.md
    REPOSITORY_TRACKED_DEPENDENCIES_GATE=FAIL
    REPOSITORY_REPRODUCIBILITY_GATE=FAIL
    SCI_ORAN_READY_GATE=FAIL
    exit_code=20

Live Doctor validation:

    SCI_ORAN_READY_GATE=PASS
    FAILURE_REASON=NONE

Fresh user-plane smoke:

    SMOKE_ID=UPSMK-20260821T200037Z-387034
    USER_PLANE_FUNCTIONAL_SMOKE_GATE=PASS
    USER_PLANE_PROCESS_CONTINUITY_GATE=PASS

## Evidence

Primary final validation evidence:

    /home/khoshaba/sci-oran-evidence/prompt12/generic-doctor-fail-closed-validation-v1

Live Doctor log SHA256:

    fa1ebbb287309e7a90825a41e32d7d1df0cffa9dea3fd1bee8152daa2827b090

Fresh user-plane smoke log SHA256:

    d0f36c3f1e0a21186277fff4921d0cd5b8abb3b9cc78580d4654c06a9b9c7b6f

Validated Doctor SHA256 before checkpoint:

    cdb6223046213d54935c0578ce1c9bff2cd100cb7869ddd6e5f106eb9dfc48a5

Validated repository policy SHA256 before checkpoint:

    085ba8d2afbb81ea6d51e87d6d7d7b87448fc51e1f7b8f6726210f2718a4d9aa

## Prompt-12 PRB continuity guardrails

The previous PRB actuator defect must not be rediscovered as a new problem.

The relevant established facts are:

1. For the 52-PRB cell, a 25 percent PRB limit corresponds to:

       floor(52 * 25 / 100) = 13 PRB

2. The earlier R02 behavior had two separate defects:

   - 25 percent was interpreted as a literal 25 PRB;
   - a later NewTx allocation path could expand allocation back up to
     approximately 48 PRB.

3. The repair covered the relevant srsRAN control/scheduler path and added
   native applied-state readback:

       PRB_ACTUATOR_APPLIED

4. R03 subsequently proved an applied maximum of:

       applied_max_prbs=13

5. Established operating points include approximately:

       48 PRB -> 17.8 Mbit/s
       13 PRB -> 7.01 Mbit/s

6. The old Prompt-12 baseline actuator must not be repeated:

       prompt12-siso-actuator-baseline25-v1
       NEVER_REPEAT

7. No E2 Control or PRB Control was executed during this Doctor repair.

8. After this Doctor block is closed, the intended experimental continuation is:

       explicit recovery-only 25 percent control
       -> native PRB_ACTUATOR_APPLIED max_prbs=13
       -> baseline verification
       -> R01 retry
       -> initial output stationarity
       -> T1: 13 PRB -> 26 PRB

The historic temporary source-repair workspace under /tmp must not be treated
as durable project state. Durable conclusions, image/source provenance, and
future repairs must be recorded in Git and evidence.

## Persistence rule

Important root causes, repaired defects, experiment boundaries, source
provenance, NEVER_REPEAT controls, validated operating points, and handoff
state must be written to repository documentation and evidence before a
Prompt or chat is considered closed.

Chat history alone is not the authoritative project record.
