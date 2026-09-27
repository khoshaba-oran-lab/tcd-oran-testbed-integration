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

## 13. Evidence-Backed Production Actuator Wrapper Scope Expansion

<!-- PROMPT12_V2_PRODUCTION_ACTUATOR_WRAPPER_SCOPE_EXPANSION_V1 -->

### 13.1 Adjudication Basis

The repository-only V2 implementation phase defined in Sections 9--12 is complete.

Subsequent read-only production-admission adjudication established that the
persistent provider and persistent reader are implemented, but a production
actuator invocation cannot yet be represented as a single tracked argv
suitable for the reader execution boundary.

The following facts were established without Docker mutation, actuator
execution, PRB control, traffic, or scientific triggering:

- the historical production execution class is a Docker container;
- the canonical actuator binary is present and executable;
- the canonical actuator binary SHA256 is
  `de71dcc0298c50c433828ec80be60bd68447ad6ef2912b2dcf3da65e10d4700f`;
- the canonical RIC configuration SHA256 is
  `940d8e1a87b8e937fea3678ca9fc47dd765f3bdf9f68f731cf6d2d47dda8be68`;
- the production image is
  `sha256:02a7181afaf1cb5892bbaaaeb3808e9db9bcb7594fa48396e3da56e210bc60bb`;
- the required Docker network is `tcd-base05-zmq_ran`;
- no tracked single-argv production actuator wrapper currently exists;
- the persistent reader already supplies the requested ratio through
  `SCI_ORAN_MAX_PRB_RATIO`;
- allowed ratio values remain exactly `25,50,75,100`;
- one accepted trigger must cause at most one actuator invocation and one
  control request;
- automatic control retry remains prohibited.

Therefore the previously frozen implementation surface is expanded by exactly
one production wrapper and its isolated test file.

### 13.2 Newly Authorised Implementation Files

The following two files are added to the authorised implementation surface:

1. `scripts/experiment-harness/prompt12-production-actuator-wrapper.py`
2. `scripts/experiment-harness/tests/test_prompt12_production_actuator_wrapper.py`

No other file is authorised for modification by this scope expansion unless a
later evidence-backed adjudication explicitly extends the scope again.

### 13.3 Frozen Wrapper Inputs

The production actuator wrapper shall accept the requested PRB ratio only via:

`SCI_ORAN_MAX_PRB_RATIO`

The variable:

- must be present;
- must contain exactly one of `25`, `50`, `75`, or `100`;
- must fail closed for every other value;
- must not have a default value.

The wrapper shall use the following frozen production execution contract:

- execution image:
  `sha256:02a7181afaf1cb5892bbaaaeb3808e9db9bcb7594fa48396e3da56e210bc60bb`;
- execution network:
  `tcd-base05-zmq_ran`;
- actuator host source:
  `/home/khoshaba/sci-oran/build/prompt12-actuator-bfd1a35b/build/examples/xApp/c/control/xapp_oran_slice_ctrl`;
- actuator container destination:
  `/opt/action11r/canonical-actuator`;
- RIC configuration host source:
  `/home/khoshaba/project/tcd-oran-testbed-integration/deploy/phase-2-flexric/tb3-runtime/configs/ric.conf`;
- RIC configuration container destination:
  `/opt/action11r/xapp_oran_sm.conf`;
- actuator entrypoint:
  `/opt/action11r/canonical-actuator`;
- actuator argv:
  `-c /opt/action11r/xapp_oran_sm.conf`;
- restart policy:
  `no`;
- security option:
  `no-new-privileges`;
- automatic removal:
  `false`.

### 13.4 Required Wrapper Behaviour

One wrapper invocation represents one admitted actuator attempt.

The wrapper shall:

1. validate `SCI_ORAN_MAX_PRB_RATIO` before any Docker mutation;
2. validate the canonical actuator binary and RIC configuration identities;
3. validate the required Docker image and network before actuator execution;
4. use a unique invocation-specific container identity;
5. create/start no more than one actuator container for one invocation;
6. pass `SCI_ORAN_MAX_PRB_RATIO` explicitly into the container environment;
7. mount the canonical actuator binary read-only;
8. mount the canonical RIC configuration read-only;
9. attach the exact frozen production network;
10. use the exact frozen entrypoint and `-c` configuration argument;
11. execute no automatic retry;
12. propagate a non-zero Docker/actuator result as wrapper failure;
13. fail closed on any precondition failure;
14. emit machine-readable evidence sufficient to attribute the invocation.

The wrapper must not implement trigger handling, ratio-binding consumption,
stationarity evaluation, scientific scheduling, or orchestration.

Those responsibilities remain in their existing V2 components.

### 13.5 Exactly-Once Boundary

The exactly-once control chain remains:

`ratio binding -> accepted TRIGGER -> persistent reader -> one wrapper invocation -> one actuator control request`

The wrapper is not a second orchestration path.

It is only the production execution adapter behind the already frozen
persistent-reader actuator boundary.

No wrapper implementation may:

- consume the FIFO trigger directly;
- read or write ratio-binding state;
- generate a second scientific trigger;
- retry an actuator request;
- alter transition order;
- redefine scientific time origin.

Scientific time origin remains:

`PRB_ACTUATOR_APPLIED`

### 13.6 Repository-Only Implementation Gate

Implementation and tests for the two newly authorised files shall initially be
repository-only.

Tests shall use mocks, stubs, temporary files, or equivalent isolated
mechanisms and shall prove at least:

- missing ratio fails closed;
- invalid ratio fails closed;
- each allowed ratio is accepted;
- binary identity mismatch fails closed;
- configuration identity mismatch fails closed;
- missing Docker image fails closed;
- missing Docker network fails closed;
- exact Docker argv construction;
- exact environment propagation;
- read-only mount semantics;
- exact entrypoint and configuration argument;
- no automatic retry;
- one invocation produces at most one Docker execution attempt;
- non-zero child status propagates as failure;
- machine-readable evidence is emitted deterministically.

During this implementation phase:

- real Docker container creation is prohibited;
- real actuator execution is prohibited;
- PRB mutation is prohibited;
- traffic generation is prohibited;
- scientific triggering is prohibited.

### 13.7 Runtime Admission Note

At the time of this adjudication:

- the required Docker image was present;
- the required Docker network `tcd-base05-zmq_ran` was not present.

This is a future runtime-admission condition, not an implementation blocker.

The wrapper implementation shall not create the missing network.

Network availability must be established through the authorised Tb3 lifecycle
path before live production admission.

### 13.8 Next Authorised Implementation Step

After this scope-expansion record is verified, the next implementation Action
may create only:

1. `scripts/experiment-harness/prompt12-production-actuator-wrapper.py`
2. `scripts/experiment-harness/tests/test_prompt12_production_actuator_wrapper.py`

No provider, reader, trigger executor, orchestration supervisor, runtime
profile, production binding, or lifecycle file is authorised for modification
by that implementation Action.

## 14. Production provider launch materializer scope expansion

Control marker:

`PROMPT12_V2_PROVIDER_LAUNCH_MATERIALIZER_SCOPE_EXPANSION_V1`

### 14.1 Scope decision

The Prompt 12 V2 production path requires a tracked repository component
that materializes the complete production provider launch argument vector
from explicit run-allocated and live-discovered inputs.

This scope expansion authorises repository-only implementation of exactly:

- `scripts/experiment-harness/prompt12-production-provider-launch-materializer.py`
- `scripts/experiment-harness/tests/test_prompt12_production_provider_launch_materializer.py`

The materializer is an argv constructor only. It MUST NOT execute the
constructed argv and this scope expansion does not admit live runtime use.

The contract schema identifier is:

`sci_oran_prompt12_v2_production_provider_launch_materializer_contract_v1`

### 14.2 Dynamic required inputs

The materializer accepts exactly four dynamic required inputs.

1. `experiment_id`
   - class: `RUN_ALLOCATED`
   - required
   - non-empty
   - no default

2. `run_id`
   - class: `RUN_ALLOCATED`
   - required
   - non-empty
   - no default

3. `fifo_path`
   - class: `LIVE_DISCOVERED`
   - required
   - non-empty
   - absolute path
   - no default

4. `ratio_binding_paths`
   - class: `RUN_ALLOCATED`
   - required
   - cardinality exactly six
   - every path non-empty
   - every path absolute
   - input order preserved
   - no default

### 14.3 Static tracked inputs

The materializer uses exactly two static tracked inputs:

1. the production local FIFO reader executable:

   `scripts/experiment-harness/prompt12-production-local-fifo-reader.py`

2. the production actuator argv containing only:

   `scripts/experiment-harness/prompt12-production-actuator-wrapper.py`

No fixture, placeholder, fallback executable, or implicit substitute is
permitted.

### 14.4 Output contract

The semantic output name is:

`provider_launch_argv`

The output type is:

`ARGV_JSON_COMPATIBLE_LIST`

The resulting argv MUST have the production reader launch shape:

- reader executable
- `--fifo-path`
- `<fifo_path>`
- `--actuator-argv-json`
- JSON array containing only the production actuator wrapper
- `--experiment-id`
- `<experiment_id>`
- `--run-id`
- `<run_id>`
- `--ratio-binding-paths-json`
- JSON-encoded ordered list of exactly six ratio-binding paths

The materializer constructs this argv and returns or emits its
representation only. It MUST NOT execute it.

### 14.5 Fail-closed conditions

The materializer MUST fail closed for every one of the following:

- missing `experiment_id`;
- empty `experiment_id`;
- missing `run_id`;
- empty `run_id`;
- missing `fifo_path`;
- empty `fifo_path`;
- non-absolute `fifo_path`;
- missing `ratio_binding_paths`;
- `ratio_binding_paths` cardinality other than six;
- any empty ratio-binding path;
- any non-absolute ratio-binding path;
- missing reader executable;
- reader executable not executable;
- missing production actuator wrapper;
- production actuator wrapper not executable;
- any unexpected extra input;
- any implicit or default substitution.

### 14.6 Forbidden responsibilities

The materializer MUST NOT:

- create a FIFO;
- start the provider;
- start the reader;
- start the actuator;
- consume a ratio binding;
- generate a scientific trigger;
- execute Docker;
- create a Docker network;
- mutate PRB state;
- generate scientific traffic;
- evaluate stationarity;
- orchestrate an experiment;
- retry control;
- replay a consumed trigger.

### 14.7 Repository-only verification boundary

Implementation verification MUST remain repository-only.

The implementation phase MUST include at least the frozen twenty contract
test cases covering valid construction and all required fail-closed
boundaries.

Before implementation commit, a separate read-only contract audit MUST
verify:

- only the two authorised future files were introduced;
- the materializer performs construction only;
- no runtime execution path was introduced;
- no default or fixture substitution was introduced;
- all frozen fail-closed conditions are covered;
- all repository-only tests pass.

No provider, reader, actuator, Docker, PRB, traffic, lifecycle, or
scientific-trigger activity is authorised by this section.

### 14.8 Admission status after this scope expansion

Recording this section authorises the future repository implementation
scope only.

Immediately after this plan update:

- production provider launch materializer implementation remains
  `NOT_IMPLEMENTED`;
- production provider launch materializer test remains
  `NOT_IMPLEMENTED`;
- live runtime admission remains `false`;
- `provider_launch_argv` MUST NOT be treated as production-resolved until
  implementation, repository-only verification, contract audit, commit,
  and push are completed.

The next phase after the scope checkpoint is the frozen repository-only
materializer implementation path. No live production admission is implied.

## Runtime-root allocator/materializer scope expansion — Recovery R5

PROMPT12_V2_RUNTIME_ROOT_ALLOCATOR_SCOPE_EXPANSION_V1

### Purpose

Close the production `runtime_root` binding without introducing an
ad-hoc runtime path or transferring directory-creation ownership away
from the persistent prearmed actuator provider.

### Current adjudication

- binding: `runtime_root`
- semantic class: `RUN_ALLOCATED`
- current resolution status: `UNRESOLVED`
- blocker:
  `TRACKED_PRODUCTION_RUNTIME_ROOT_ALLOCATOR_ABSENT`

The repository contains no tracked production producer of the
provider's required `--runtime-root` argument and no tracked
runtime-root allocator mechanism.

### Future component role

The authorised future component role is:

`RUNTIME_ROOT_ALLOCATOR_MATERIALIZER`

It is a path materializer only. It does not create runtime resources.

### Required dynamic inputs

The future materializer shall require exactly these semantic inputs:

1. `experiment_id`
   - class: `RUN_ALLOCATED`
   - required
   - non-empty
   - no implicit default

2. `run_id`
   - class: `RUN_ALLOCATED`
   - required
   - non-empty
   - no implicit default

3. `tracked_runtime_parent`
   - class: `STATIC_TRACKED`
   - required
   - absolute
   - canonical
   - existing directory
   - no implicit default

### Output contract

The output semantic is:

`runtime_root`

Properties:

- type: absolute filesystem path;
- class: `RUN_ALLOCATED`;
- deterministically bound to `experiment_id` and `run_id`;
- located directly under the exact tracked runtime parent;
- must not exist at materialization time;
- must be suitable for subsequent provider validation.

### Ownership boundary

The future materializer:

- computes the `runtime_root` path only;
- MUST NOT create `runtime_root`;
- MUST NOT create the FIFO.

The persistent prearmed actuator provider retains exclusive ownership
of:

- validating that the runtime-root parent exists and is canonical;
- validating that `runtime_root` does not already exist;
- creating `runtime_root` exclusively;
- creating the canonical FIFO beneath that runtime root.

### Required fail-closed conditions

The future materializer shall fail closed on at least:

- missing `experiment_id`;
- empty `experiment_id`;
- missing `run_id`;
- empty `run_id`;
- missing `tracked_runtime_parent`;
- relative `tracked_runtime_parent`;
- non-canonical tracked runtime parent;
- missing tracked runtime parent;
- tracked runtime parent not a directory;
- implicit default substitution;
- fixture or placeholder substitution;
- output escaping the exact tracked runtime parent;
- output already existing.

### Forbidden responsibilities

The future materializer MUST NOT:

- create `runtime_root`;
- create a FIFO;
- start the provider;
- start the persistent reader;
- start the actuator;
- execute Docker;
- create or modify a Docker network;
- mutate PRB state;
- generate scientific traffic;
- generate or consume a scientific trigger;
- perform automatic retries;
- replay a control operation;
- evaluate stationarity;
- perform lifecycle mutation.

### Resolution rule

`runtime_root` MUST remain present in
`unresolved_runtime_bindings` until all of the following are complete:

1. tracked materializer implementation;
2. repository-only verification and tests;
3. read-only contract audit;
4. commit;
5. push;
6. authoritative provider-contract closure.

No live runtime admission is authorised by this scope expansion.
