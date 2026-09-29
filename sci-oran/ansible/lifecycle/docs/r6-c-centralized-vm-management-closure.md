# Recovery R6-C: Centralized VM Management Closure

STATUS=PASS
R6_C=PASS
DATE=2026-09-29

## Canonical checkpoint

CANONICAL_HEAD=b7fb26bff18fcadb3637cc8d457f380add1d6ba6

AUTHORITATIVE_CONTROLLER=coll.vntu.org
AUTHORITATIVE_REPOSITORY=/home/khoshaba/project/tcd-oran-testbed-integration
AUTHORITATIVE_BRANCH=main

## Convergence

COLL_CONVERGENCE=PASS
GITHUB_CONVERGENCE=PASS
TB3_CONVERGENCE=PASS

At closure, coll.vntu.org, GitHub main, and the subordinate tb3-dell
checkout resolve to the same canonical Git checkpoint.

## Centralized management result

R6-C established a controller-managed multi-VM lifecycle model.

The validated implementation provides:

HOST_IDENTITY_PARAMETERIZATION=PASS
EXPLICIT_TARGET_LIFECYCLE_WRAPPER=PASS
AUTHORITATIVE_REPOSITORY_ROOT_BINDING=PASS
CONTROLLED_DAY_START_EXPLICIT_TARGET=PASS
OPERATOR_CONTRACT_ALIGNMENT=PASS

## Inventory model

The managed VM group is:

sci_oran_vms

The controller-local runtime inventory remains intentionally untracked.

Host-specific identity is supplied through:

host_vars/<inventory-host>.yml

Group-wide parameters are supplied through:

group_vars/sci_oran_vms.yml

The current validated runtime target is:

tb3-dell

Future compatible experimental VMs must be introduced through inventory
and host-specific variables rather than independent lifecycle source trees.

## Explicit target safety boundary

Every state-changing lifecycle operation requires exactly one explicit
inventory target.

The canonical lifecycle interface is equivalent to:

tb3-lifecycle.sh <operation> --target <inventory-host> --confirm

The target must resolve as a member of sci_oran_vms.

The wrapper binds the target to Ansible through:

--limit <inventory-host>

Therefore:

IMPLICIT_MULTI_VM_MUTATION=FORBIDDEN

An omitted target fails closed.

An unknown target fails closed.

A state-changing operation must not implicitly execute against the entire
sci_oran_vms group.

## Controlled day-start safety boundary

The controlled day-start path also requires an explicit target.

Read-only qualification:

tb3-controlled-day-start.sh --preflight --target <inventory-host>

Execution requires both:

1. an explicit target;
2. the separate SCI_ORAN_DAY_START_AUTHORISATION contract.

The selected target is passed to Ansible through --limit.

Automatic retry remains forbidden.

## Authoritative source model

The authoritative Ansible source tree is:

/home/khoshaba/project/tcd-oran-testbed-integration/sci-oran/ansible

The lifecycle wrapper derives its default Ansible root from its repository
location.

The former default dependency on:

$HOME/sci-oran/ansible

has been removed from the canonical lifecycle wrapper.

Explicit environment overrides remain available when deliberately supplied.

## Preserved lifecycle semantics

The existing validated lifecycle model remains preserved for:

- deploy
- day-start
- day-stop
- teardown
- recover
- reset
- preflight

Existing confirmation, operation-ID, fail-closed, exactly-once, and
read-only-before-retry principles remain in force.

The validated R6-A day-stop behavior must not be weakened.

## Scientific boundary

R6-C infrastructure work did not authorize scientific experimentation.

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES

No Prompt-12 T1-T6 experiment acquisition, scientific traffic, or PRB
control is authorized by this closure.

## Closure

CENTRALIZED_VM_MANAGEMENT_GATE=PASS
THREE_LEVEL_GIT_CONVERGENCE_GATE=PASS
IMPLICIT_MULTI_VM_MUTATION=FORBIDDEN
R6_C=PASS

NEXT_WORKSTREAM=R6-D_STORAGE_ARCHITECTURE
