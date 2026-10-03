# Recovery R6-J Canonical Lifecycle Variable Contract Completion

STATUS=PASS
UTC_TIME=2026-10-03T05:07:37Z

## Failed lifecycle transaction

FAILED_DAY_START_OPERATION_ID=lifecycle-day-start-20261003T050314Z-ed632b6e
FAILED_RECOVERY_OPERATION_ID=lifecycle-recover-20261003T050314Z-ed632b6e
FAILED_TEARDOWN_OPERATION_ID=lifecycle-teardown-20261003T050314Z-ed632b6e
FAILED_DEPLOY_OPERATION_ID=lifecycle-deploy-20261003T050314Z-ed632b6e

FAILED_OPERATION_IDS_MUST_NOT_BE_REPLAYED=YES
FAILED_TRANSACTION_CHANGED_TASKS=NO

FAILED_LOG=/home/khoshaba/sci-oran/staging/r6-j-resumption/controller-logs/lifecycle-day-start-20261003T050314Z-ed632b6e.log
FAILED_LOG_SHA256=c5fdbe14b3989c549d05b6e400bfad559c8fe995f2a2976f58a9dff12383ba1c

## Root cause

J03_R3_FAILURE_ROOT_CAUSE=REPOSITORY_HOST_CONTRACT_MISSING_EXPECTED_BRANCH_BINDING
J03_R3_FAILURE_SUBCLASS=HOSTVARS_BINDING_REPAIR_WAS_INCOMPLETE_FOR_PREFLIGHT_REQUIRED_VARIABLE_SET

The branch binding was not absent from the repository configuration model.
Its canonical repository source already existed at:

sci-oran/ansible/group_vars/sci_oran_vms.yml

with:

sci_oran_expected_branch: "main"

The previous lifecycle repair explicitly bound only:

sci-oran/ansible/host_vars/tb3-dell.yml

Therefore the repository group contract was not visible when the canonical
repository lifecycle playbook was executed against the external controller
inventory.

## Canonical variable-contract model

EXTERNAL_INVENTORY=/home/khoshaba/sci-oran/ansible/inventory.ini
EXTERNAL_INVENTORY_ROLE=CONNECTION_AND_MEMBERSHIP

CANONICAL_GROUP_CONTRACT=sci-oran/ansible/group_vars/sci_oran_vms.yml
CANONICAL_GROUP_CONTRACT_ROLE=GROUP_WIDE_LIFECYCLE_POLICY

CANONICAL_HOST_CONTRACT=sci-oran/ansible/host_vars/tb3-dell.yml
CANONICAL_HOST_CONTRACT_ROLE=HOST_IDENTITY_AND_REPOSITORY_BINDINGS

GROUP_CONTRACT_EXPECTED_BRANCH=main
HOST_CONTRACT_EXPECTED_INVENTORY_HOST=tb3-dell
HOST_CONTRACT_EXPECTED_HOSTNAME=tb3-dell
HOST_CONTRACT_REPOSITORY_ROOT=/home/khoshaba/project/tcd-oran-testbed-integration

## Repair

CANONICAL_LIFECYCLE_WRAPPER=sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh

The canonical lifecycle wrapper now explicitly loads repository-controlled
variables in this order:

1. -e "@$GROUP_VARS_FILE"
2. -e "@$HOST_VARS_FILE"

The host contract is later in the extra-vars sequence so any deliberate
host-specific binding has precedence over a group-wide default.

No branch variable was duplicated into host_vars.

## Qualification

WRAPPER_SHA256_BEFORE=2ad882670b3246d2779f8328b88db770fcd7dc2a1bcdaede9ad4f7851dc321a0
WRAPPER_SHA256_AFTER=f5d469e3c3eb9825ed8ec050699aca52a3d93fa96e0c1746dd91c57fde69d8e6

GROUPVARS_SHA256=019c593b5da823ff9c351fb637a59f93839cd4050496e5f98c5f205d6e67605d
HOSTVARS_SHA256=9b2f4d2e11a66dcfd04fd5e8bd05ec881b8ed64daff9aa11af21733e8028ecad
INVENTORY_SHA256=1c2a0cb44efa677afd2f43c62bb23ab9204d8aabbcfa0338e4810bf43952c09c

GROUPVARS_EXPECTED_BRANCH_GATE=PASS
HOSTVARS_BRANCH_DUPLICATION_GATE=PASS
GROUPVARS_PATH_GATE=PASS
HOSTVARS_PATH_GATE=PASS
GROUPVARS_FAIL_CLOSED_GATE=PASS
HOSTVARS_FAIL_CLOSED_GATE=PASS
GROUPVARS_EXTRA_VARS_GATE=PASS
HOSTVARS_EXTRA_VARS_GATE=PASS
VARIABLE_PRECEDENCE_ORDER_GATE=PASS
COMPLETE_EFFECTIVE_CONTRACT_GATE=PASS
TARGET_MEMBERSHIP_GATE=PASS
BOUND_DAY_START_SYNTAX_GATE=PASS
MISSING_TARGET_FAIL_CLOSED_GATE=PASS
FAKE_TARGET_FAIL_CLOSED_GATE=PASS

## Execution boundary

DAY_START_EXECUTED_BY_THIS_REPAIR=NO
LIFECYCLE_OPERATION_PERFORMED_BY_THIS_REPAIR=NO
TB3_MUTATION_PERFORMED_BY_THIS_REPAIR=NO
DOCKER_MUTATION_PERFORMED_BY_THIS_REPAIR=NO

TRAFFIC_GENERATION_PERFORMED=NO
PRB_CONTROL_PERFORMED=NO
PROMPT12_PRECONTROL_EXECUTED=NO
PROMPT12_TRIGGER_PERFORMED=NO
SCIENTIFIC_OPERATION_PERFORMED=NO

R6J_GATE_02=NOT_YET_PASS

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO

A future canonical day-start requires repository convergence on tb3-dell, a
fresh lifecycle transaction, a new operation ID, and separate authorization.
