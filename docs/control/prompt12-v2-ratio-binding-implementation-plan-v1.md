# Prompt 12 V2 Pre-Trigger Ratio Binding Implementation Plan

Status: FROZEN_IMPLEMENTATION_PLAN

## 1. Purpose

Implement transition-specific PRB ratio binding for the Prompt 12 bounded six-transition production sequence while preserving:

- one persistent reader for the complete T1-T6 sequence;
- one persistent trigger FIFO;
- the exact scientific trigger token `TRIGGER`;
- no ratio value inside the trigger payload;
- ratio binding before scientific trigger;
- exactly-once actuator execution;
- no automatic trigger replay;
- no automatic reader or actuator restart;
- scientific time origin at `PRB_ACTUATOR_APPLIED`.

The frozen design contract is:

`experiments/manifests/prompt12-v2-pretrigger-ratio-binding-contract-v1.json`

## 2. Canonical Transition Order

Each transition T1-T6 shall follow exactly:

1. previous post-step stationarity PASS, or initial admission PASS;
2. materialize transition-specific ratio binding;
3. validate `RATIO_BOUND=PASS`;
4. execute exactly one scientific `TRIGGER`;
5. consume exactly one valid ratio binding;
6. execute exactly one actuator invocation;
7. obtain applied readback;
8. evaluate post-step stationarity.

Canonical target sequence:

| Transition | Target ratio |
|---|---:|
| T1 | 50 |
| T2 | 75 |
| T3 | 100 |
| T4 | 75 |
| T5 | 50 |
| T6 | 25 |

## 3. Frozen Implementation Surface

No additional production component shall be added to the implementation scope unless a later evidence-backed Action proves it necessary.

### 3.1 New component

Create:

`scripts/experiment-harness/prompt12-pretrigger-ratio-binding-writer.py`

Create corresponding test:

`scripts/experiment-harness/tests/test_prompt12_pretrigger_ratio_binding_writer.py`

Responsibilities:

- receive experiment identity;
- receive run identity;
- receive transition label;
- receive transition index;
- receive requested ratio;
- receive explicit output path;
- validate ratio against `{25,50,75,100}`;
- materialize one transition-specific JSON binding;
- create output exclusively;
- never overwrite an existing binding;
- compute/report binding SHA256;
- produce `RATIO_BOUND=PASS` only after successful exclusive creation;
- perform no trigger;
- perform no actuator execution;
- perform no PRB control;
- perform no traffic action.

Required binding fields:

- `schema`;
- `binding_id`;
- `experiment_id`;
- `run_id`;
- `transition_label`;
- `transition_index`;
- `requested_ratio_pct`;
- `created_utc`.

Required schema value:

`sci_oran_prompt12_v2_pretrigger_ratio_binding_v1`

## 4. Existing Components Requiring Modification

### 4.1 Persistent reader

Modify:

`scripts/experiment-harness/prompt12-production-local-fifo-reader.py`

Modify test:

`scripts/experiment-harness/tests/test_prompt12_production_local_fifo_reader.py`

Required changes:

- remove reader-lifetime PRB ratio binding as the production mechanism;
- accept one explicit ratio-binding path or binding-location contract required by the runtime profile;
- for every accepted `TRIGGER`, validate the current transition binding before actuator execution;
- fail closed on missing binding;
- fail closed on malformed binding;
- fail closed on stale binding;
- fail closed on reused binding;
- fail closed on experiment/run/transition identity mismatch;
- fail closed on invalid ratio;
- build actuator environment per execution;
- set `SCI_ORAN_MAX_PRB_RATIO` from the current validated binding;
- consume a binding at most once;
- retain exactly one actuator execution per accepted valid trigger;
- retain `shell=False`;
- retain no retry and no replay.

Reader tests must cover at least:

- six sequential bindings with ratios `50,75,100,75,50,25`;
- one persistent reader across all six;
- binding missing;
- binding malformed;
- ratio invalid;
- binding identity mismatch;
- binding already consumed;
- repeated trigger against consumed binding;
- actuator failure without retry;
- FIFO EOF without replay;
- ratio propagation into actuator environment.

### 4.2 Runtime profile materializer

Modify:

`scripts/experiment-harness/prompt12-bounded-runtime-profile-materializer.py`

Modify test:

`scripts/experiment-harness/tests/test_prompt12_bounded_runtime_profile_materializer.py`

Required changes:

- materialize the ratio-binding path namespace required by the production reader and writer;
- preserve exclusive run-directory allocation;
- preserve existing FIFO validation;
- preserve non-execution semantics;
- expose exactly six transition-specific binding paths or one explicit binding directory with deterministic T1-T6 paths;
- produce no binding file itself unless explicitly required by the frozen contract.

### 4.3 Runtime profile template contract

Modify:

`experiments/manifests/prompt12-bounded-sequence-runtime-profile-template-contract-v1.json`

Modify its existing test if necessary:

`scripts/experiment-harness/tests/test_prompt12_bounded_runtime_profile_template_contract.py`

Required change:

- add the live/runtime-materialized ratio-binding path contract;
- keep ratio target sequence unchanged;
- do not move ratio into the scientific trigger token.

### 4.4 Production binding builder

Modify:

`scripts/experiment-harness/prompt12-bounded-production-binding-builder.py`

Modify test:

`scripts/experiment-harness/tests/test_prompt12_bounded_production_binding_builder.py`

Required transition shape:

- `label`;
- `ratio_bind_command`;
- `trigger_command`;
- `post_stationarity_command`.

`ratio_bind_command` must precede `trigger_command`.

The builder must only construct argv. It must execute nothing.

### 4.5 Sequence plan builder

Modify:

`scripts/experiment-harness/prompt12-bounded-sequence-plan-builder.py`

Modify test:

`scripts/experiment-harness/tests/test_prompt12_bounded_sequence_plan_builder.py`

Required changes:

- require `ratio_bind_command` for every T1-T6 transition;
- validate it as an explicit non-empty argv;
- preserve transition order T1-T6;
- reject bindings missing `ratio_bind_command`;
- reject unexpected transition structure;
- execute nothing.

### 4.6 Orchestration supervisor

Modify:

`scripts/experiment-harness/prompt12-bounded-orchestration-supervisor.py`

Modify test:

`scripts/experiment-harness/tests/test_prompt12_bounded_orchestration_supervisor.py`

Required live order per transition:

1. prior stationarity gate PASS;
2. execute `ratio_bind_command`;
3. require zero return code / `RATIO_BOUND` success;
4. only then execute `trigger_command`;
5. prohibit later trigger if ratio binding fails;
6. proceed to post-step stationarity only after successful trigger path.

Tests must prove:

- ratio-bind executes before trigger;
- failed ratio-bind prevents trigger;
- one ratio-bind attempt per admitted transition;
- one trigger attempt per admitted transition;
- failure at Tn prevents Tn trigger and all later triggers as appropriate;
- no second orchestration path is introduced.

## 5. Components Frozen as NO_CHANGE

The following components shall not be modified by this implementation phase unless a later read-only adjudication proves the frozen assumption false.

### 5.1 Persistent provider

NO_CHANGE:

`scripts/experiment-harness/prompt12-persistent-prearmed-actuator-provider.py`

Reason:

- provider owns FIFO lifecycle and reader process lifecycle;
- transition-specific ratio binding belongs inside the persistent reader execution boundary;
- provider must remain ratio-agnostic.

### 5.2 Trigger executor

NO_CHANGE:

`scripts/experiment-harness/prompt12-precontrol-trigger-executor.py`

Reason:

- trigger payload remains exactly `TRIGGER`;
- ratio remains outside the scientific trigger payload;
- trigger executor remains responsible only for authorised exactly-once FIFO trigger write semantics.

### 5.3 Dry-run six-transition orchestrator

NO_CHANGE:

`scripts/experiment-harness/prompt12-six-transition-orchestrator.py`

Reason:

- it is a dry-run reasoning/state component;
- live production execution is handled by the binding-plan-supervisor path.

## 6. Binding Consumption Semantics

A valid transition binding shall be single-use.

Required properties:

- binding identity is unique;
- binding cannot be silently overwritten;
- binding cannot be reused;
- reader must detect already-consumed state;
- successful consumption must be attributable to the exact binding identity;
- accepted trigger with invalid or consumed binding must fail closed before actuator execution.

The implementation may use an atomic filesystem state transition, for example:

`binding.json -> binding.consumed.json`

or an equivalently strong exclusive/atomic mechanism.

The exact mechanism must be tested before production admission.

## 7. Fail-Closed Conditions

The following must prevent actuator execution:

- missing binding;
- invalid JSON;
- invalid schema;
- invalid ratio;
- stale binding;
- experiment ID mismatch;
- run ID mismatch;
- transition label mismatch;
- transition index mismatch;
- duplicate binding identity;
- previously consumed binding;
- ratio-bind command failure;
- uncertain binding state.

Scientific trigger replay remains prohibited after an uncertain trigger write.

## 8. Evidence Requirements

Before every trigger the production path shall make available evidence containing at least:

- `binding_id`;
- `experiment_id`;
- `run_id`;
- `transition_label`;
- `transition_index`;
- `requested_ratio_pct`;
- `binding_file_path`;
- `binding_file_sha256`;
- `binding_created_utc`;
- `RATIO_BOUND=PASS`.

Consumption evidence shall include at least:

- `binding_id`;
- binding consumed state;
- trigger accepted state;
- actuator execution count.

`RATIO_BOUND` is not the scientific time origin.

Scientific time origin remains:

`PRB_ACTUATOR_APPLIED`

## 9. Implementation Sequence

The repository implementation shall proceed in this order:

1. implement and test ratio-binding writer;
2. extend and test runtime-profile materializer/template;
3. extend and test persistent reader;
4. extend and test production binding builder;
5. extend and test sequence plan builder;
6. extend and test orchestration supervisor;
7. run combined repository-only regression suite;
8. inspect exact diff;
9. commit implementation checkpoint;
10. push implementation checkpoint;
11. only after repository state is frozen, perform separate production admission planning.

No production runtime action is authorised by this plan.

## 10. Checkpoint Policy

Every implementation sub-stage shall obey ONE-ACTION rules.

Before production admission there must be:

- repository-only implementation;
- isolated tests with temporary FIFOs/files/stubs only;
- no real actuator;
- no FlexRIC control;
- no traffic;
- no PRB mutation;
- no scientific trigger;
- clean regression result;
- explicit commit checkpoint;
- explicit push checkpoint.

## 11. Scope Freeze

In-scope production implementation files:

1. `scripts/experiment-harness/prompt12-pretrigger-ratio-binding-writer.py`
2. `scripts/experiment-harness/tests/test_prompt12_pretrigger_ratio_binding_writer.py`
3. `scripts/experiment-harness/prompt12-production-local-fifo-reader.py`
4. `scripts/experiment-harness/tests/test_prompt12_production_local_fifo_reader.py`
5. `scripts/experiment-harness/prompt12-bounded-runtime-profile-materializer.py`
6. `scripts/experiment-harness/tests/test_prompt12_bounded_runtime_profile_materializer.py`
7. `experiments/manifests/prompt12-bounded-sequence-runtime-profile-template-contract-v1.json`
8. `scripts/experiment-harness/tests/test_prompt12_bounded_runtime_profile_template_contract.py`
9. `scripts/experiment-harness/prompt12-bounded-production-binding-builder.py`
10. `scripts/experiment-harness/tests/test_prompt12_bounded_production_binding_builder.py`
11. `scripts/experiment-harness/prompt12-bounded-sequence-plan-builder.py`
12. `scripts/experiment-harness/tests/test_prompt12_bounded_sequence_plan_builder.py`
13. `scripts/experiment-harness/prompt12-bounded-orchestration-supervisor.py`
14. `scripts/experiment-harness/tests/test_prompt12_bounded_orchestration_supervisor.py`

Frozen NO_CHANGE:

- persistent provider;
- trigger executor;
- dry-run six-transition orchestrator.

Any expansion of this implementation surface requires a separate evidence-backed adjudication.

## 12. Next Authorised Phase

After this plan is committed and pushed, the next implementation phase begins with only:

`IMPLEMENT_AND_TEST_PRETRIGGER_RATIO_BINDING_WRITER`

No other implementation sub-stage is implicitly authorised.
