# Recovery R6-C: Centralized VM Management Design Contract

STATUS=DEFINED
R6_C_DESIGN_CONTRACT=PASS
DATE=2026-09-29

## Purpose

R6-C defines how coll.vntu.org centrally manages tb3-dell and future
compatible experimental VMs.

The existing validated lifecycle implementation is reused.

A full lifecycle rewrite is not required.

LIFECYCLE_REWRITE_REQUIRED=NO
PARAMETERIZATION_REQUIRED=YES

## Controller authority

The authoritative working repository is:

HOST=coll.vntu.org
PATH=/home/khoshaba/project/tcd-oran-testbed-integration
BRANCH=main

The authoritative Ansible source tree is:

/home/khoshaba/project/tcd-oran-testbed-integration/sci-oran/ansible

Lifecycle source must originate from this repository.

The legacy controller operational tree:

/home/khoshaba/sci-oran/ansible

must not remain an independent source of lifecycle code.

## Inventory model

The controller-local runtime inventory remains intentionally untracked:

sci-oran/ansible/inventory.ini

The tracked reproducible template remains:

sci-oran/ansible/inventory.ini.example

Therefore:

LOCAL_INVENTORY_TRACKED=NO
INVENTORY_TEMPLATE_TRACKED=YES

Environment-specific connection data such as ansible_host and ansible_user
belong in the controller-local inventory.

Adding a compatible VM should primarily require a new inventory host entry
and its host-specific variables.

## Inventory group

The management group remains:

sci_oran_vms

The group may contain one or more compatible experimental VMs.

Example conceptual structure:

    [sci_oran_vms]
    tb3-dell ...
    future-vm-01 ...
    future-vm-02 ...

The presence of multiple hosts must never cause an implicit destructive
operation against every host in the group.

## Explicit lifecycle target

Every state-changing lifecycle operation must select exactly one inventory
target explicitly.

EXPLICIT_VM_TARGET_REQUIRED=YES

The canonical wrapper interface should evolve toward a form equivalent to:

    tb3-lifecycle.sh day-start --target tb3-dell --confirm
    tb3-lifecycle.sh day-stop  --target tb3-dell --confirm

The wrapper must pass the selected target to Ansible using an explicit limit
equivalent to:

    --limit <inventory-host>

A missing target for a state-changing lifecycle operation must fail closed.

An invalid or unresolved target must fail closed.

Implicit mutation of all hosts in sci_oran_vms is forbidden.

## Host identity contract

Host identity must be parameterized from inventory data rather than hard-coded
globally in tb3-preflight.yml.

Current hard-coded values:

    sci_oran_expected_inventory_host: "tb3-dell"
    sci_oran_expected_hostname: "tb3-dell"

must not remain the multi-VM authority model.

HOST_IDENTITY_SOURCE=INVENTORY_VARIABLES

Each managed host must provide the host-specific identity information required
by the fail-closed preflight contract.

At minimum the preflight must verify that:

1. the explicitly selected inventory host is the host being evaluated;
2. the observed remote hostname matches the expected hostname for that host;
3. the required repository and runtime paths exist;
4. the repository branch is the required canonical branch;
5. lifecycle prerequisites pass before mutation.

The validated fail-closed preflight principle remains mandatory.

## Repository root on managed VMs

The currently validated managed-host repository location is:

/home/khoshaba/project/tcd-oran-testbed-integration

This may remain the initial Tb3-compatible default.

If future compatible VMs require a different path, that path must become an
explicit inventory variable rather than a manual per-VM source edit.

## Controller source-root resolution

The lifecycle wrapper must execute playbooks from the authoritative repository
source tree.

It must not depend by default on a separately maintained copy under:

$HOME/sci-oran/ansible

Preferred resolution model:

1. derive the Ansible source root from the canonical wrapper/repository
   location;
2. allow an explicit SCI_ORAN_ANSIBLE_ROOT override only when deliberately
   supplied;
3. allow SCI_ORAN_INVENTORY to select a controller-local inventory;
4. preserve fail-closed checks for missing inventory and playbook paths.

AUTHORITATIVE_ANSIBLE_SOURCE=REPOSITORY

## Existing lifecycle components to preserve

The following validated lifecycle operations remain reusable:

- deploy
- day-start
- day-stop
- teardown
- recover
- reset
- preflight
- capture-state
- finalize-operation

Existing operation-ID and exactly-once protections remain in force.

Existing validated day-stop behavior must not be weakened.

## Safety rules

For state-changing lifecycle operations:

1. explicit --confirm remains required;
2. exactly one VM target must be explicit;
3. preflight must execute before mutation;
4. consumed lifecycle operation IDs must never be replayed;
5. no implicit whole-group destructive execution is allowed;
6. failures after partial mutation require read-only adjudication before retry;
7. manual Docker stop/down is not the normal lifecycle path.

## Scalability objective

A future compatible VM should be introduced mainly through:

1. inventory entry;
2. host-specific variables;
3. reproducible deployment qualification.

It should not require:

- independent lifecycle source trees;
- manual Python environment maintenance;
- VM-specific edits to common lifecycle playbooks;
- another authoritative Git repository;
- manual reconstruction of controller logic.

TARGET_ARCHITECTURE=CONTROLLER_MANAGED_MULTI_VM

## Scientific boundary

R6-C infrastructure work does not authorize:

- scientific traffic;
- PRB control;
- Prompt-12 T1-T6;
- new experiment acquisition.

Scientific experiments remain frozen until the required R6 platform readiness
workstreams are closed.

## Implementation order

The next implementation work must remain bounded.

First implementation objective:

EXPLICIT_TARGET_PARAMETERIZATION

This includes:

- explicit target argument in the lifecycle wrapper;
- fail-closed target validation;
- Ansible --limit binding;
- inventory-based host identity variables;
- preservation of current tb3-dell behavior.

Only after this is qualified should controller source-root migration be
implemented.

## Decision summary

LIFECYCLE_REWRITE_REQUIRED=NO
PARAMETERIZATION_REQUIRED=YES
EXPLICIT_VM_TARGET_REQUIRED=YES
HOST_IDENTITY_SOURCE=INVENTORY_VARIABLES
AUTHORITATIVE_ANSIBLE_SOURCE=REPOSITORY
LOCAL_INVENTORY_TRACKED=NO
INVENTORY_TEMPLATE_TRACKED=YES
TARGET_ARCHITECTURE=CONTROLLER_MANAGED_MULTI_VM
NEXT_IMPLEMENTATION_STEP=EXPLICIT_TARGET_PARAMETERIZATION
