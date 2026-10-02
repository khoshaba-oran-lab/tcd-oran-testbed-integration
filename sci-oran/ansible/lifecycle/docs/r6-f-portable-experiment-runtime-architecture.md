# Recovery R6-F Portable Experiment Runtime Architecture

STATUS=ARCHITECTURE_DEFINED
WORKSTREAM=R6-F_PORTABLE_EXPERIMENT_RUNTIME
ARCHITECTURE_DATE=2026-10-02

## Purpose

R6-F defines a portable experiment-runtime architecture for Sci_O-RAN
without requiring identical Python installations, virtual-environment paths,
or binary wheel sets on all hosts.

The portability boundary is capability-based rather than based on exact
cross-host package identity.

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO

## Evidence basis

R6F_CONTROLLER_PYTHON=CPython_3.9.25
R6F_CONTROLLER_JSONSCHEMA=4.25.1

R6F_TB3_PYTHON=CPython_3.12.3
R6F_TB3_JSONSCHEMA=4.10.3

R6F_JSONSCHEMA_CONSUMER_COUNT=6
R6F_STDLIB_ONLY_PRODUCTION_COUNT=24
R6F_THIRD_PARTY_PRODUCTION_COUNT=6

R6F_TB3_DRAFT202012_IMPORT=PASS
R6F_TB3_DRAFT202012_BEHAVIOUR=PASS
R6F_ALL_CONSUMER_STATIC_API_GATE=PASS
R6F_ALL_CONSUMER_MODULE_LOAD_GATE=PASS
R6F_ALL_CONSUMER_CLI_LOAD_GATE=PASS

R6F_EXACT_PYTHON_VERSION_EQUALITY_REQUIRED=NO
R6F_EXACT_JSONSCHEMA_VERSION_EQUALITY_REQUIRED=NO
R6F_JSONSCHEMA_DRAFT202012_CAPABILITY_REQUIRED=YES

## Rejected portability models

R6F_CONTROLLER_VENV_COPY_AS_PORTABILITY_MODEL=FORBIDDEN
R6F_IDENTICAL_ABSOLUTE_VENV_PATH_REQUIREMENT=FORBIDDEN
R6F_CP39_BINARY_WHEEL_REUSE_ON_CP312=FORBIDDEN

The existing controller wheelhouse contains a CPython-3.9-specific rpds-py
binary wheel and therefore is not a universal cross-Python wheelhouse.

A portable runtime must not treat the controller venv directory as the
portable artifact.

## Selected architecture

R6F_ARCHITECTURE=CAPABILITY_BASED_INTERPRETER_PLUS_MATERIALIZED_RUNTIME_PROFILE
R6F_ARCHITECTURE_FINALISED=YES

R6F_LAYER_1=PYTHON3_STDLIB_RUNTIME
R6F_LAYER_2=JSONSCHEMA_DRAFT202012_CAPABILITY
R6F_LAYER_3=HOST_RUNTIME_PROFILE
R6F_LAYER_4=INTERPRETER_AND_PATH_MATERIALIZATION
R6F_LAYER_5=FAIL_CLOSED_PREFLIGHT

## Layer 1 - Python stdlib runtime

The production Prompt-12 runtime should use the host Python interpreter when
all required standard-library capabilities are present.

A specific Python minor version is not itself the portability contract.

R6F_STDLIB_RUNTIME_REQUIRED=YES
R6F_SPECIFIC_PYTHON_MINOR_REQUIRED=NO

## Layer 2 - JSON Schema capability

Tools that require jsonschema depend on the Draft 2020-12 capability surface,
not on an exact jsonschema package version.

The required capability includes:

- Draft202012Validator import;
- Draft202012Validator.check_schema;
- Draft202012Validator construction;
- validation of valid instances;
- rejection of invalid instances;
- ValidationError where consumed by the tool.

R6F_JSONSCHEMA_POLICY=CAPABILITY_BASED
R6F_JSONSCHEMA_DRAFT202012_CAPABILITY_REQUIRED=YES
R6F_EXACT_JSONSCHEMA_VERSION_REQUIRED=NO

## Layer 3 - Host runtime profile

Host-specific values must be represented as runtime-profile data rather than
being silently embedded as controller-specific constants.

The host runtime profile must be explicit and fail closed.

At minimum it must identify:

- host identity;
- selected Python executable;
- required interpreter capabilities;
- runtime-root parent;
- evidence-root location where relevant;
- tool paths required by the bounded experiment runtime.

R6F_HOST_RUNTIME_PROFILE_REQUIRED=YES
R6F_HOST_SPECIFIC_VALUES_MUST_BE_EXPLICIT=YES

## Layer 4 - Interpreter and path materialization

The executable selected for a run must be resolved for the current host and
then materialized into the concrete runtime profile.

The current frozen production configuration contains a controller-specific
Python path:

/home/khoshaba/sci-oran/venvs/prompt12-py39-jsonschema-4.25.1/bin/python

That path is historical configuration input and must not remain the portable
cross-host binding model.

R6F_HOST_SPECIFIC_INTERPRETER_PATH_MUST_BE_MATERIALIZED=YES
R6F_HARDCODED_CONTROLLER_VENV_PATH_IN_PORTABLE_PROFILE=FORBIDDEN
R6F_INTERPRETER_SELECTION_MUST_BE_EXPLICIT=YES
R6F_INTERPRETER_SELECTION_MUST_BE_FAIL_CLOSED=YES

## Layer 5 - Fail-closed portability preflight

Before a portable experiment runtime is admitted, the selected interpreter
must be checked without launching scientific traffic or control actions.

The preflight must verify at least:

- interpreter exists;
- interpreter is executable;
- Python can start;
- stdlib runtime is usable;
- Draft 2020-12 capability is present when required;
- required tools exist;
- required paths are absolute and valid;
- runtime profile contains no implicit controller-only fallback.

R6F_FAIL_CLOSED_CAPABILITY_PREFLIGHT_REQUIRED=YES
R6F_PREFLIGHT_MAY_RUN_SCIENTIFIC_TRIGGER=NO
R6F_PREFLIGHT_MAY_GENERATE_TRAFFIC=NO
R6F_PREFLIGHT_MAY_CONTROL_PRB=NO

## Dependency bootstrap boundary

Dependency installation and scientific execution are separate responsibilities.

A missing capability may block runtime admission, but runtime admission must
not silently install packages.

Package bootstrap, if later required, must be an explicitly authorised,
independently qualified operation.

R6F_DEPENDENCY_BOOTSTRAP_SEPARATE_FROM_SCIENTIFIC_EXECUTION=YES
R6F_RUNTIME_PREFLIGHT_AUTO_INSTALL_ALLOWED=NO
R6F_RUNTIME_PROFILE_AUTO_INSTALL_ALLOWED=NO

## Implementation boundary

The future R6-F implementation must provide the following responsibilities:

R6F_IMPLEMENTATION_RESPONSIBILITY_01=CAPABILITY_PREFLIGHT
R6F_IMPLEMENTATION_RESPONSIBILITY_02=HOST_RUNTIME_PROFILE
R6F_IMPLEMENTATION_RESPONSIBILITY_03=INTERPRETER_PATH_MATERIALIZATION
R6F_IMPLEMENTATION_RESPONSIBILITY_04=PORTABLE_FROZEN_CONFIG_BINDING
R6F_IMPLEMENTATION_RESPONSIBILITY_05=FAIL_CLOSED_TESTS
R6F_IMPLEMENTATION_RESPONSIBILITY_06=CROSS_HOST_QUALIFICATION

The implementation must preserve the existing Prompt-12 exactly-once,
evidence, lifecycle and scientific-safety boundaries.

R6F_IMPLEMENTATION_MAY_RUN_SCIENTIFIC_OPERATION=NO
R6F_IMPLEMENTATION_MAY_RUN_PROMPT12_TRIGGER=NO
R6F_IMPLEMENTATION_MAY_GENERATE_TRAFFIC=NO
R6F_IMPLEMENTATION_MAY_CONTROL_PRB=NO

## Frozen configuration migration rule

The existing frozen configuration must not be modified opportunistically.

Its controller-specific python_executable field is now classified as a
portability defect to be repaired by a separately authorised R6-F
implementation Action.

R6F_EXISTING_FROZEN_CONFIG_PORTABILITY_DEFECT=CONFIRMED
R6F_EXISTING_FROZEN_CONFIG_MUTATION_AUTHORISED=NO

## Architecture closure state

R6F_ARCHITECTURE_CANDIDATE_TB3_QUALIFIED=YES
R6F_ARCHITECTURE_FINALISED=YES
R6F_IMPLEMENTATION_AUTHORISED=NO

R6F_NEXT_PHASE=PORTABLE_RUNTIME_IMPLEMENTATION_DESIGN_AND_BOUNDED_REALISATION

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO
