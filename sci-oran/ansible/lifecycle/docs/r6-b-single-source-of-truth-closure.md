# Recovery R6-B: Single Source of Truth Closure

STATUS=PASS
R6_B=PASS
DATE=2026-09-29

## Authoritative working repository

HOST=coll.vntu.org
PATH=/home/khoshaba/project/tcd-oran-testbed-integration
BRANCH=main
HEAD=5b3cff46cd82829aa77b388d33fcd0e85ca96bd0

This repository on coll.vntu.org is the authoritative working repository
for the Sci_O-RAN platform.

## GitHub role

REMOTE=git@github.com:khoshaba-oran-lab/tcd-oran-testbed-integration.git
ROLE=PUBLISHED_REMOTE

At R6-B closure:

GITHUB_MAIN=5b3cff46cd82829aa77b388d33fcd0e85ca96bd0

GitHub is the published remote for the authoritative repository.
It is not a separate independently maintained experimental control state.

## tb3-dell role

HOST=tb3-dell
ROLE=SUBORDINATE_RUNTIME_CHECKOUT

Repository:

/home/khoshaba/project/tcd-oran-testbed-integration

At R6-B closure:

TB3_BRANCH=main
TB3_HEAD=5b3cff46cd82829aa77b388d33fcd0e85ca96bd0
TB3_WORKTREE=CLEAN

tb3-dell must not become an independent manually maintained control centre.

Its repository checkout is subordinate to the authoritative repository
maintained on coll.vntu.org.

## Authority model

The required model is:

coll.vntu.org authoritative working repository
    ->
GitHub published remote
    ->
tb3-dell subordinate runtime checkout

Future compatible experimental VMs must follow the same model.

Adding another VM must not create another authoritative repository state.

## Validated lifecycle consolidation

The validated R6-A lifecycle material is now contained in the
authoritative repository.

Checkpoint commit:

5b3cff46cd82829aa77b388d33fcd0e85ca96bd0

Commit subject:

infra(r6): consolidate validated Tb3 lifecycle control

Validated consolidated artifacts include:

- sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh
- sci-oran/ansible/lifecycle/docs/r6-a-validated-tb3-day-stop.md
- sci-oran/ansible/lifecycle/playbooks/tb3-day-stop.yml
- sci-oran/ansible/lifecycle/playbooks/tb3-preflight.yml

## Operational rules

1. Architectural and lifecycle source changes originate from the
   authoritative repository on coll.vntu.org.

2. Important architectural decisions must be persisted in that repository.

3. tb3-dell is a runtime target, not an independent source of truth.

4. VM-side manual source divergence must not be accepted as normal operation.

5. GitHub main should represent the published canonical state.

6. Runtime-generated evidence and transient state remain outside Git and are
   handled by the dedicated R6 storage/evidence architecture.

7. Scientific experiments remain frozen until the R6 platform readiness
   workstreams are completed.

## Closure result

COMPETING_AUTHORITATIVE_GIT_STATES=NO
SINGLE_SOURCE_OF_TRUTH_GATE=PASS
R6_B=PASS

NEXT_WORKSTREAM=R6-C_CENTRALIZED_VM_MANAGEMENT
