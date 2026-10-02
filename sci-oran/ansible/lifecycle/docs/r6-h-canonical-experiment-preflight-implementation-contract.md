# Recovery R6-H Canonical Experiment Preflight Implementation Contract

STATUS=IMPLEMENTATION_CONTRACT_DEFINED
UTC=2026-10-02T17:12:19Z

## Workstream

WORKSTREAM=R6-H_CANONICAL_EXPERIMENT_PREFLIGHT

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO

## Authoritative architecture inheritance

R6H_ARCHITECTURE_DECISION=EXTEND_EXISTING_GENERIC_PREFLIGHT

R6H_CANONICAL_GENERIC_PREFLIGHT_AUTHORITY=scripts/experiment-harness/lib/preflight.sh
R6H_GENERIC_EXPERIMENT_ENTRYPOINT=scripts/experiment-harness/run-experiment.sh

R6H_PLATFORM_READINESS_PROVIDER=scripts/sci-oran-doctor.sh
R6H_PORTABLE_RUNTIME_PROVIDER=scripts/experiment-harness/r6-f-portable-runtime-preflight.py

R6H_NEW_PARALLEL_GENERIC_PREFLIGHT=FORBIDDEN
R6H_REIMPLEMENT_R6F_CAPABILITY_VALIDATION=NO

## Exact implementation file set

R6H_IMPLEMENTATION_FILE_1=scripts/experiment-harness/run-experiment.sh
R6H_IMPLEMENTATION_FILE_2=scripts/experiment-harness/lib/preflight.sh
R6H_IMPLEMENTATION_FILE_3=scripts/experiment-harness/tests/test_generic_preflight.py

R6H_IMPLEMENTATION_FILE_COUNT=3

The implementation phase shall remain bounded to these three files unless a
future failure proves that this contract is incomplete.

The following production providers shall not be modified by the canonical
preflight integration:

R6H_DOCTOR_SOURCE_MUTATION_ALLOWED=NO
R6H_PORTABLE_PROVIDER_SOURCE_MUTATION_ALLOWED=NO
R6H_USER_PLANE_SMOKE_SOURCE_MUTATION_ALLOWED=NO
R6H_PROMPT12_PRECONTROL_SOURCE_MUTATION_ALLOWED=NO

## Binding ownership

R6H_IMPLEMENTATION_INTERFACE_DECISION=EXPLICIT_NAMED_BINDINGS
R6H_BINDING_OWNER=GENERIC_EXPERIMENT_ENTRYPOINT

The generic experiment entrypoint owns the explicit values required by the
portable-runtime provider and passes them to the sourced canonical preflight
library through a named environment contract.

R6H_BINDING_TRANSPORT=EXPLICIT_NAMED_ENVIRONMENT_CONTRACT_TO_SOURCED_PREFLIGHT_LIBRARY

R6H_PYTHON_EXECUTABLE_BINDING=SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE
R6H_JSONSCHEMA_POLICY_BINDING=SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA
R6H_PORTABLE_ADMISSION_OUTPUT_BINDING=SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT

## Binding rules

SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE shall contain an explicit absolute
interpreter path for the host executing the experiment preflight.

SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA shall contain exactly:

yes

or:

no

SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT shall contain an explicit
absolute path for the bounded portable-runtime admission artifact.

R6H_BINDING_DEFAULTS_ALLOWED=NO
R6H_IMPLICIT_SYS_EXECUTABLE_FALLBACK_ALLOWED=NO
R6H_IMPLICIT_PATH_PYTHON_LOOKUP_ALLOWED=NO
R6H_CONTROLLER_VENV_FALLBACK_ALLOWED=NO
R6H_IMPLICIT_OUTPUT_PATH_DEFAULT_ALLOWED=NO

R6H_BINDINGS_REQUIRED_BEFORE_PORTABLE_PROVIDER_CALL=YES

Missing or malformed required bindings shall fail the generic experiment
preflight before scientific execution.

## Provider ordering

The implementation order is frozen:

R6H_PREFLIGHT_ORDER_1=PLATFORM_READINESS
R6H_PREFLIGHT_ORDER_2=PORTABLE_RUNTIME_BINDING_VALIDATION
R6H_PREFLIGHT_ORDER_3=PORTABLE_RUNTIME_ADMISSION
R6H_PREFLIGHT_ORDER_4=GENERIC_PREFLIGHT_FINAL_ADJUDICATION

Platform readiness must pass before the portable-runtime provider is executed.

R6H_PLATFORM_FAIL_SHORT_CIRCUITS_PORTABLE_PROVIDER=YES

Portable-runtime admission must pass before the generic preflight can pass.

R6H_PORTABLE_PASS_REQUIRED_FOR_GENERIC_PASS=YES

A provider failure shall never be converted into a successful generic
preflight result.

R6H_GENERIC_PREFLIGHT_FAIL_CLOSED=YES

## Platform provider contract

The existing doctor integration remains the platform-readiness provider.

R6H_PLATFORM_READY_SOURCE=SCI_ORAN_READY_GATE
R6H_PLATFORM_FAILURE_PROVENANCE_SOURCE=FAILURE_REASON

The existing generic output surface shall remain compatible:

SCI_ORAN_PREFLIGHT_READY_GATE=PASS|FAIL
SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=<integer>
SCI_ORAN_PREFLIGHT_FAILURE_REASON=<reason>

## Portable provider invocation contract

The canonical generic preflight shall invoke:

scripts/experiment-harness/r6-f-portable-runtime-preflight.py

using exactly the explicit values bound through:

SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE
SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA
SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT

The provider CLI bindings are:

--python-executable
--require-jsonschema
--output

R6H_PORTABLE_RUNTIME_ADMISSION_SCHEMA=sci_oran_r6_f_portable_runtime_admission_v1

A successful provider result requires:

R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=PASS
ADMISSION_QUALIFICATION_GATE=PASS

and zero provider exit status.

R6H_PORTABLE_PROVIDER_ZERO_EXIT_REQUIRED=YES
R6H_PORTABLE_PROVIDER_PASS_MARKER_REQUIRED=YES

A non-zero exit status or missing/non-PASS portable gate shall fail the
generic preflight.

## Failure provenance

The implementation shall expose enough provenance to distinguish platform
failure from portable-runtime failure.

R6H_PROVENANCE_PLATFORM_READY_GATE_REQUIRED=YES
R6H_PROVENANCE_PLATFORM_FAILURE_REASON_REQUIRED=YES
R6H_PROVENANCE_PLATFORM_EXIT_CODE_REQUIRED=YES

R6H_PROVENANCE_PORTABLE_RUNTIME_GATE_REQUIRED=YES
R6H_PROVENANCE_PORTABLE_RUNTIME_EXIT_CODE_REQUIRED=YES
R6H_PROVENANCE_PORTABLE_RUNTIME_ADMISSION_PATH_REQUIRED=YES

R6H_PROVENANCE_CANONICAL_PREFLIGHT_READY_GATE_REQUIRED=YES
R6H_PROVENANCE_CANONICAL_PREFLIGHT_FAILURE_REASON_REQUIRED=YES

The future implementation may introduce explicit portable-provider provenance
markers under the SCI_ORAN_PREFLIGHT namespace, provided the existing platform
markers remain backward compatible.

## Bounded evidence-write semantics

The portable-runtime provider requires an explicit admission output artifact.

R6H_PORTABLE_ADMISSION_ARTIFACT_CLASS=BOUNDED_PREFLIGHT_EVIDENCE
R6H_PORTABLE_ADMISSION_ARTIFACT_WRITE_ALLOWED=YES
R6H_PORTABLE_ADMISSION_ARTIFACT_PATH_MUST_BE_EXPLICIT=YES
R6H_PORTABLE_ADMISSION_ARTIFACT_PATH_DEFAULT_ALLOWED=NO

For R6-H:

R6H_READ_ONLY_SEMANTICS=NO_RUNTIME_LIFECYCLE_SCIENTIFIC_OR_CONFIGURATION_MUTATION

The explicitly requested bounded admission-evidence write is not classified as
a forbidden runtime/scientific mutation.

R6H_BOUNDED_PREFLIGHT_EVIDENCE_WRITE_EXCLUDED_FROM_MUTATION_PROHIBITION=YES

## Generic-preflight forbidden responsibilities

R6H_GENERIC_PREFLIGHT_MAY_RUN_USER_PLANE_SMOKE=NO
R6H_GENERIC_PREFLIGHT_MAY_RUN_PING=NO
R6H_GENERIC_PREFLIGHT_MAY_RUN_IPERF=NO
R6H_GENERIC_PREFLIGHT_MAY_CONTROL_PRB=NO

R6H_GENERIC_PREFLIGHT_MAY_RUN_PROMPT12_PRECONTROL=NO
R6H_GENERIC_PREFLIGHT_MAY_RUN_PROMPT12_TRIGGER=NO

R6H_GENERIC_PREFLIGHT_MAY_INSTALL_PACKAGES=NO
R6H_GENERIC_PREFLIGHT_MAY_CREATE_VENV=NO

R6H_GENERIC_PREFLIGHT_MAY_RUN_LIFECYCLE_MUTATION=NO
R6H_GENERIC_PREFLIGHT_MAY_RUN_DOCKER_MUTATION=NO

R6H_GENERIC_PREFLIGHT_MAY_PERFORM_HIDDEN_RECOVERY=NO

## Prompt-12 separation

Prompt-12-specific admission remains outside the generic experiment preflight.

R6H_PROMPT12_SPECIFIC_COUPLING_IN_GENERIC_PREFLIGHT=FORBIDDEN

The implementation must not call:

scripts/experiment-harness/prompt12-precontrol-freshness.py

and must not add Prompt-12 actuator, stationarity, PRB, workload, trigger or
applied-readback semantics to the generic preflight library.

## Backward compatibility

Existing run-experiment behaviour unrelated to R6-H binding/admission shall be
preserved.

R6H_EXISTING_RUNNER_TRAFFIC_INTERFACE_MUST_REMAIN_COMPATIBLE=YES
R6H_EXISTING_PLATFORM_PREFLIGHT_MARKERS_MUST_REMAIN_COMPATIBLE=YES

The integration shall not silently change the meaning of existing traffic,
KPM, cooldown, metadata snapshot or postcheck arguments.

## Test contract

A new dedicated generic-preflight regression test is required:

R6H_GENERIC_PREFLIGHT_TEST_FILE=scripts/experiment-harness/tests/test_generic_preflight.py

At minimum the test suite shall cover:

R6H_TEST_01=PLATFORM_FAIL_SHORT_CIRCUITS_PORTABLE_PROVIDER
R6H_TEST_02=MISSING_PYTHON_BINDING_FAILS
R6H_TEST_03=MISSING_JSONSCHEMA_POLICY_BINDING_FAILS
R6H_TEST_04=MISSING_PORTABLE_OUTPUT_BINDING_FAILS
R6H_TEST_05=INVALID_JSONSCHEMA_POLICY_BINDING_FAILS
R6H_TEST_06=NONABSOLUTE_PYTHON_BINDING_FAILS
R6H_TEST_07=NONABSOLUTE_OUTPUT_BINDING_FAILS
R6H_TEST_08=PORTABLE_PROVIDER_NONZERO_PROPAGATES_FAIL
R6H_TEST_09=PORTABLE_PROVIDER_NONPASS_GATE_PROPAGATES_FAIL
R6H_TEST_10=ALL_REQUIRED_PROVIDERS_PASS
R6H_TEST_11=PORTABLE_ADMISSION_PATH_PROVENANCE_PRESENT
R6H_TEST_12=NO_PROMPT12_SPECIFIC_COUPLING
R6H_TEST_13=NO_ACTIVE_TRAFFIC_GENERATION_PATH
R6H_TEST_14=NO_PACKAGE_BOOTSTRAP_PATH
R6H_TEST_15=EXISTING_PLATFORM_MARKERS_REMAIN_COMPATIBLE

## H09 implementation macro acceptance

The future H09 implementation macro may perform, on coll.vntu.org:

1. precondition verification;
2. bounded edits to the three authorised implementation files;
3. shell syntax validation;
4. Python/unit/offline tests;
5. portable-provider regression tests;
6. static forbidden-responsibility scans;
7. exact mutation-scope verification;
8. staged-diff verification;
9. commit;
10. push;
11. local/GitHub convergence verification.

R6H_H09_ONE_MACRO_ACTION_ALLOWED=YES

H09 shall stop at the first failure.

R6H_H09_AUTOMATIC_REPAIR_AFTER_FAILURE=NO
R6H_H09_AUTOMATIC_RETRY_AFTER_FAILURE=NO

If H09 fails after any source mutation, the next Action shall be read-only
forensics.

## H09 mutation boundary

R6H_H09_SOURCE_MUTATION_ALLOWED=YES
R6H_H09_ALLOWED_FILE_COUNT=3

R6H_H09_ALLOWED_FILE_1=scripts/experiment-harness/run-experiment.sh
R6H_H09_ALLOWED_FILE_2=scripts/experiment-harness/lib/preflight.sh
R6H_H09_ALLOWED_FILE_3=scripts/experiment-harness/tests/test_generic_preflight.py

R6H_H09_TB3_MUTATION_ALLOWED=NO
R6H_H09_LIFECYCLE_OPERATION_ALLOWED=NO
R6H_H09_DOCKER_MUTATION_ALLOWED=NO
R6H_H09_TRAFFIC_GENERATION_ALLOWED=NO
R6H_H09_PRB_CONTROL_ALLOWED=NO
R6H_H09_PROMPT12_TRIGGER_ALLOWED=NO
R6H_H09_SCIENTIFIC_OPERATION_ALLOWED=NO

## Implementation contract acceptance

R6H_BINDING_OWNERSHIP_GATE=PASS
R6H_BINDING_TRANSPORT_GATE=PASS
R6H_FAIL_CLOSED_ORDERING_GATE=PASS
R6H_BOUNDED_EVIDENCE_WRITE_GATE=PASS
R6H_PROMPT12_SEPARATION_GATE=PASS
R6H_H09_SCOPE_GATE=PASS

R6H_IMPLEMENTATION_CONTRACT_GATE=PASS

## Safety boundary

PRODUCTION_SOURCE_MUTATION_PERFORMED_BY_H08=NO
MASTER_PLAN_MUTATION_PERFORMED_BY_H08=NO

TB3_MUTATION_PERFORMED=NO
LIFECYCLE_OPERATION_PERFORMED=NO
DOCKER_MUTATION_PERFORMED=NO

GENERIC_PREFLIGHT_EXECUTED=NO
DOCTOR_EXECUTED=NO
PORTABLE_PREFLIGHT_EXECUTED=NO

USER_PLANE_SMOKE_EXECUTED=NO
ACTIVE_USER_PLANE_PROBE_EXECUTED=NO
TRAFFIC_GENERATION_PERFORMED=NO

PRB_CONTROL_PERFORMED=NO
PROMPT12_TRIGGER_PERFORMED=NO
SCIENTIFIC_OPERATION_PERFORMED=NO

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES
PROMPT12_RESUMPTION_AUTHORISED=NO
