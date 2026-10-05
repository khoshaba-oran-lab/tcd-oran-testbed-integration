# R6 Offline Sprint 01 — implementation design

R6_OFFLINE_SPRINT01_IMPLEMENTATION_DESIGN_V1_BEGIN

SPRINT_ID=R6_OFFLINE_SPRINT01
SPRINT_NAME=CANONICAL_T2_EXECUTION_CLOSURE
DESIGN_STATUS=FROZEN
EXECUTION_STATUS=NOT_STARTED
OFFLINE_READY=NO
LIVE_READY=NO

## Goal

Implement the minimum reusable repository-controlled path required to prepare
one resumed Prompt-12 T2 transition from 26 to 39 PRBs.

The implementation is offline until all acceptance gates pass.

## Architectural responsibility split

Reusable scientific orchestration shall be implemented with Ansible.

Existing tested Python and shell programs remain leaf tools.

The existing full T1-to-T6 supervisor remains unchanged and is not the
canonical resumed T2-only consumer.

The resume precontrol materializer remains a pure materializer and shall not be
converted into an execution supervisor.

NEW_PYTHON_SUPERVISOR=PROHIBITED
GENERATED_PRODUCTION_WRAPPER=PROHIBITED
NEW_SHELL_ORCHESTRATION_FRAMEWORK=PROHIBITED

## Minimum implementation fileset

New Ansible playbook:

sci-oran/ansible/experiments/prompt12/playbooks/prompt12-resume-single-transition.yml

New leaf materializer:

scripts/experiment-harness/prompt12-resume-single-transition-materializer.py

New unit test:

scripts/experiment-harness/tests/test_prompt12_resume_single_transition_materializer.py

Control documents may be updated only to record implementation and
qualification state.

## Single-transition materializer contract

The materializer performs no traffic, Docker, FIFO, actuator, PRB or
scientific-control action.

Inputs:

- canonical production binding manifest;
- resume-precontrol materialization;
- explicit transition index.

For Sprint 01 the required transition index is 2.

The materialized execution description shall contain:

- schema;
- transition label;
- transition index;
- traffic command;
- initial-precontrol command;
- ratio-bind command;
- trigger command;
- pure post-step stationarity command;
- finalization command.

For transition T2 the pure post-step stationarity command must be derived from
the existing production binding semantics without retaining the T3 precontrol
handoff wrapper.

Required invariants:

FIRST_SCIENTIFIC_TRANSITION=T2
INITIAL_TRANSITION_INDEX=2
SYNTHETIC_PRIOR_TRANSITION_EVENTS=NO
SKIPPED_TRANSITION_BINDINGS_CONSUMED=NO
T3_HANDOFF_PRESENT=NO
T3_TRIGGER_PRESENT=NO
COMMAND_EXECUTED=NO
CONTROL_EXECUTED=NO
TRAFFIC_EXECUTED=NO

The materializer must fail closed on malformed or inconsistent source
artifacts.

## Ansible orchestration contract

The playbook is the reusable orchestration layer.

Its intended live order is:

1. validate approved repository/input state;
2. materialize the T2-only execution description;
3. start the bounded traffic session asynchronously;
4. execute resume-aware T2 initial-precontrol;
5. enforce the pre-step minimum duration and stationarity gate;
6. execute the already-approved T2 ratio-binding step;
7. execute the exactly-once T2 trigger;
8. obtain authoritative applied PRB readback;
9. execute pure T2 post-step stationarity;
10. execute finalization;
11. terminate/collect owned traffic execution state;
12. emit bounded evidence and final result.

The scientific trigger task must never have automatic retries.

AUTOMATIC_TRIGGER_RETRY=PROHIBITED
AUTOMATIC_TRIGGER_REPLAY=PROHIBITED

An unexpected result after a possible trigger write must fail closed and
preserve evidence rather than attempt another trigger.

T3 precontrol and T3 trigger are outside this sprint.

T3_PRECONTROL_AUTHORISED=NO
T3_TRIGGER_AUTHORISED=NO

## Existing leaf tools to reuse

The implementation shall reuse existing repository tools where their current
contracts fit, including:

- resume precontrol materializer;
- bounded traffic session adapter;
- ratio-binding tooling;
- precontrol trigger executor;
- authoritative PRB readback;
- bounded stationarity tooling;
- bounded finalization tooling;
- existing provider/reader/actuator path.

Their scientific semantics must not be silently reimplemented in Ansible.

## Offline acceptance gates

Before OFFLINE_READY may become YES:

PYTHON_UNIT_TESTS=PASS
ANSIBLE_SYNTAX=PASS
SINGLE_TRANSITION_SCHEMA_GATE=PASS
T2_SELECTION_GATE=PASS
T1_BINDING_CONSUMPTION_GATE=NO_CONSUMPTION
T3_HANDOFF_GATE=ABSENT
T3_TRIGGER_GATE=ABSENT
FULL_SEQUENCE_SUPERVISOR_MUTATION_GATE=NO_CHANGE
OFFLINE_TRAFFIC_EXECUTION_GATE=NO
OFFLINE_FIFO_WRITE_GATE=NO
OFFLINE_PRB_MUTATION_GATE=NO
EXACT_COMMAND_SEQUENCE_GATE=PASS
FAIL_CLOSED_GATE=PASS

No Tb3 live start or scientific execution is authorised by this design.

R6_OFFLINE_SPRINT01_IMPLEMENTATION_DESIGN_V1_END
