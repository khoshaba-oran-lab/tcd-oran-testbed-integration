# Recovery R6 Master Plan

STATUS=ACTIVE
PLAN_ROLE=AUTHORITATIVE_R6_WORKSTREAM_ORDER
AUTHORITATIVE_CONTROLLER=coll.vntu.org
AUTHORITATIVE_REPOSITORY=/home/khoshaba/project/tcd-oran-testbed-integration
AUTHORITATIVE_BRANCH=main

## Purpose

This document is the authoritative ordering source for Recovery R6.

Local implementation details, diagnostics, evidence findings, and optional
backlog tasks must not replace, reorder, or bypass this workstream sequence.

A later workstream must not begin merely because an implementation opportunity
is discovered during an earlier workstream.

Any deliberate change to this plan requires a separate explicit decision and
repository-controlled update.

## Global execution rules

1. Work one Action at a time.

2. Classify each completed Action as PASS, FAIL, BLOCKED, or NOT_EXECUTED
   before selecting the next Action.

3. Prefer read-only qualification before state-changing operations.

4. Consequential mutations require an explicit authorization boundary.

5. Failed or partially executed operation identifiers must not be replayed
   where exactly-once semantics apply.

6. Scientific traffic, PRB control, experiment triggers, lifecycle operations,
   storage operations, and repository operations remain distinct control
   responsibilities.

7. Important architectural decisions and workstream closure states must be
   persisted in the authoritative repository.

8. coll.vntu.org is the authoritative controller and working repository.

9. GitHub main is the published canonical remote.

10. Runtime VM repository checkouts are subordinate runtime checkouts and must
    converge to the authoritative published state.

11. Nonblocking backlog items must not silently become blockers for the current
    workstream.

12. A later workstream must not be substituted for the current workstream
    merely because it is easier, more interesting, or immediately actionable.

## Recovery R6 workstream sequence

The authoritative sequence is:

R6_A=Current lifecycle closure
R6_B=Single Source of Truth
R6_C=Centralized VM Management
R6_D=Storage Architecture
R6_E=External Runtime Evidence
R6_F=Portable Experiment Runtime
R6_G=Canonical Lifecycle
R6_H=Canonical Experiment Preflight
R6_I=Legacy Data Catalogue
R6_J=Resume Prompt-12

The order above is normative unless this master plan is explicitly revised.

## R6-A - Current lifecycle closure

PURPOSE=Close and preserve the validated Tb3 lifecycle boundary.
STATUS=CLOSED_PASS

Canonical evidence:

sci-oran/ansible/lifecycle/docs/r6-a-validated-tb3-day-stop.md

Closure established that the validated lifecycle behavior must be preserved and
must not be replaced by ad-hoc manual runtime control.

## R6-B - Single Source of Truth

PURPOSE=Establish one authoritative repository and eliminate competing control states.
STATUS=CLOSED_PASS

Canonical closure:

sci-oran/ansible/lifecycle/docs/r6-b-single-source-of-truth-closure.md

Established authority model:

coll.vntu.org authoritative working repository
    ->
GitHub published remote
    ->
subordinate runtime checkout

## R6-C - Centralized VM Management

PURPOSE=Move VM lifecycle management under the authoritative controller and repository.
STATUS=CLOSED_PASS

Canonical closure:

sci-oran/ansible/lifecycle/docs/r6-c-centralized-vm-management-closure.md

Established explicit-target, inventory-driven, multi-VM lifecycle management
without permitting implicit mutation of all managed VMs.

## R6-D - Storage Architecture

PURPOSE=Separate transient runtime/acquisition storage from authoritative retained evidence and release storage.
STATUS=CLOSED_PASS

Canonical closure:

sci-oran/ansible/lifecycle/docs/r6-d-storage-architecture-closure.md

Established:

C0_REPOSITORY_CONTROL_PLANE=PASS
C1_RUNTIME_EPHEMERAL_CONFIGURATION=PASS
C2_VM_LOCAL_ACQUISITION_CONFIGURATION=PASS
C3_CONTROLLER_RETAINED_EVIDENCE=PASS
C4_RELEASE_TIER_SEPARATION=PASS

PROSPECTIVE_SCIENTIFIC_USE_STORAGE_READINESS=PASS
HISTORICAL_BULK_MIGRATION_REQUIRED_FOR_PROSPECTIVE_USE=NO
HISTORICAL_BULK_MIGRATION_STATUS=NONBLOCKING_BACKLOG

The historical bulk migration backlog does not block progression to R6-E.

## R6-E - External Runtime Evidence

PURPOSE=Define and qualify how runtime evidence external to Git is discovered, identified, referenced, and preserved under the authoritative control model.
STATUS=CLOSED_PASS

R6-E must address runtime evidence that exists outside the repository while
preserving provenance and avoiding silent dependency on undocumented local
state.

R6-E execution requires separate admission and authorization.

R6-E must not itself execute Prompt-12 scientific triggers unless a later
explicit scientific admission permits them.

## R6-F - Portable Experiment Runtime

PURPOSE=Make experiment runtime dependencies portable and reproducible across compatible execution hosts.
STATUS=ACTIVE

R6-F follows R6-E.

It must not begin before R6-E is formally closed unless this master plan is
explicitly revised.

## R6-G - Canonical Lifecycle

PURPOSE=Consolidate the complete intended experiment-platform lifecycle into one canonical repository-controlled operational model.
STATUS=NOT_STARTED

R6-G follows R6-F.

## R6-H - Canonical Experiment Preflight

PURPOSE=Define a canonical preflight that proves experiment admission conditions before scientific execution.
STATUS=NOT_STARTED

R6-H follows R6-G.

## R6-I - Legacy Data Catalogue

PURPOSE=Catalogue existing historical and legacy evidence without making bulk historical migration a prerequisite for prospective work.
STATUS=NOT_STARTED

R6-I follows R6-H.

Historical evidence migration/adoption policy remains separate from prospective
storage readiness.

## R6-J - Resume Prompt-12

PURPOSE=Return to Prompt-12 scientific work only after the Recovery R6 platform-readiness sequence has been completed and separately admitted.
STATUS=NOT_STARTED

R6-J is the first workstream in this plan that explicitly targets resumption of
Prompt-12 scientific work.

R6-J does not authorize a scientific trigger merely by becoming the current
workstream.

Scientific execution still requires the applicable experiment-specific
admission, exactly-once, evidence, runtime, and authorization gates.

## Current authoritative state

R6_A_STATUS=CLOSED_PASS
R6_B_STATUS=CLOSED_PASS
R6_C_STATUS=CLOSED_PASS
R6_D_STATUS=CLOSED_PASS
R6_E_STATUS=CLOSED_PASS
R6_F_STATUS=ACTIVE
R6_G_STATUS=NOT_STARTED
R6_H_STATUS=NOT_STARTED
R6_I_STATUS=NOT_STARTED
R6_J_STATUS=NOT_STARTED

CURRENT_COMPLETED_WORKSTREAM=R6-E_EXTERNAL_RUNTIME_EVIDENCE
NEXT_WORKSTREAM=R6-F_PORTABLE_EXPERIMENT_RUNTIME

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
R6_E_EXECUTION_AUTHORISED=NO
R6_F_EXECUTION_AUTHORISED=NO
PROMPT12_RESUMPTION_AUTHORISED=NO

## Backlog classification

HISTORICAL_BULK_MIGRATION_STATUS=NONBLOCKING_BACKLOG

This backlog must not be allowed to reorder the R6 sequence.

Additional nonblocking items discovered during later workstreams must be
recorded separately rather than silently inserted ahead of the current
authoritative workstream.

## Plan-control invariant

PLAN_DRIFT_ALLOWED=NO
IMPLICIT_REORDERING_ALLOWED=NO
UNAUTHORISED_WORKSTREAM_JUMP_ALLOWED=NO

The next workstream after the current closed R6-E state is:

NEXT_WORKSTREAM=R6-F_PORTABLE_EXPERIMENT_RUNTIME

Execution of R6-F requires a separate Action and explicit authorization.


## R6-E closure and R6-F transition checkpoint

TRANSITION_DATE=2026-10-02
R6_E_CLOSURE_FILE=sci-oran/ansible/lifecycle/docs/r6-e-external-runtime-evidence-closure.md
R6_E_CLOSURE_SHA256=db9bc50f8637b38f492cf0ca0d193906411b9da4b1e2ee4eb8c6c7534a1a8dc6
R6_E_IMPLEMENTATION_HEAD=184884e081c34bd8b4c8bc711218babcda41231e

R6F_EXACT_TOOLCHAIN_PORTABILITY_GAP=OPEN
R6F_EXACT_TOOLCHAIN_PORTABILITY_GAP_CLASSIFICATION=NEXT_WORKSTREAM_INPUT
R6F_EXACT_TOOLCHAIN_PORTABILITY_GAP_BLOCKS_R6E_CLOSURE=NO

R6_E_TO_R6_F_TRANSITION=PASS
