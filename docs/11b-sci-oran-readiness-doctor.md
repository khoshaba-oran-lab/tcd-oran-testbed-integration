# Sci_O-RAN Prompt 11B — Comprehensive Read-Only Testbed Doctor

## 1. Purpose

Prompt 11B implements a comprehensive read-only readiness diagnostic for the
Sci_O-RAN Tb3 testbed.

The principal implementation is located in:

- `scripts/sci-oran-doctor.sh`

The readiness decision is integrated with the reproducible experiment preflight
layer through:

- `scripts/experiment-harness/lib/preflight.sh`

The canonical final doctor decision is represented by
`SCI_ORAN_READY_GATE=PASS|FAIL` together with `FAILURE_REASON`.

The implementation follows fail-closed semantics: a missing, stale,
inconsistent, or failed mandatory condition must not be interpreted as PASS.

## 2. Read-only contract

The doctor is intended to inspect and validate the current testbed state without
deliberately changing the runtime configuration being evaluated.

The validated diagnostic result included:

- `DOCTOR_READ_ONLY_GATE=PASS`

Prompt 11B therefore provides a readiness check, not a runtime actuator.

A successful `SCI_ORAN_READY_GATE=PASS` must not be interpreted as completion of
the Runtime Actuation Gate.

## 3. Principal readiness gates

The comprehensive doctor evaluates the following principal gates:

- `HOST_READINESS_GATE`
- `HOST_RESOURCE_READINESS_GATE`
- `CONTAINER_READINESS_GATE`
- `NETWORK_READINESS_GATE`
- `ZMQ_READINESS_GATE`
- `N2_READINESS_GATE`
- `E2_READINESS_GATE`
- `E2SM_RC_READINESS_GATE`
- `UE_SESSION_READINESS_GATE`
- `USER_PLANE_READINESS_GATE`
- `TRAFFIC_HARNESS_READINESS_GATE`
- `REPOSITORY_REPRODUCIBILITY_GATE`
- `PROCESS_CONTINUITY_GATE`

The final validated doctor runs reported PASS for all of these gates.

## 4. User-plane readiness

User-plane readiness is verified functionally rather than only through static
configuration checks.

The validated implementation includes checks for:

- user-plane policy and policy contract;
- presence and freshness of user-plane evidence;
- UE user-plane interface availability;
- UE-to-UPF routing;
- UE-to-UPF ICMP connectivity;
- TUN traffic counter changes;
- user-plane process continuity;
- functional user-plane smoke testing;
- runtime resolution and runtime fingerprint consistency;
- diagnostic toolbox identity;
- container image identity;
- side-effect control.

These checks are aggregated into `USER_PLANE_READINESS_GATE`.

The final validated runs reported:

- `USER_PLANE_READINESS_GATE=PASS`

## 5. Traffic harness readiness

The doctor verifies that the experiment traffic harness required for subsequent
Sci_O-RAN experiments is structurally usable.

Checks include file existence, executable state, shell syntax, traffic-window
syntax, CLI contract, required arguments, dispatch logic, and command execution
path.

The aggregate validated result was:

- `TRAFFIC_HARNESS_READINESS_GATE=PASS`

## 6. Process continuity

Runtime identities are checked across the diagnostic interval so that a PASS
result is not constructed from inconsistent runtime states.

The implementation validates:

- end-of-run process capture;
- process fingerprint consistency;
- aggregate process continuity.

The validated result was:

- `PROCESS_CONTINUITY_GATE=PASS`

## 7. Readiness artifact

The doctor generates a machine-readable readiness artifact under:

`/tmp/sci-oran/readiness/`

Each run has a run-specific artifact and a current copy is published as:

`/tmp/sci-oran/readiness/latest.env`

Artifact processing includes:

- root-directory validation;
- artifact construction;
- atomic publication;
- latest-copy publication;
- schema/value validation;
- run/latest consistency validation;
- SHA-256 calculation.

The aggregate validated result was:

- `READINESS_ARTIFACT_GATE=PASS`

## 8. Readiness freshness

The readiness result must describe the current runtime state rather than stale
evidence.

Freshness validation includes:

- readiness ID coherence;
- timestamp parsing;
- temporal ordering;
- maximum run duration;
- user-plane evidence age;
- user-plane stored-age coherence;
- process continuity;
- artifact availability;
- final decision latency.

The aggregate validated result was:

- `READINESS_FRESHNESS_GATE=PASS`

One final validated run completed the doctor readiness procedure in 12 seconds
while maintaining coherent user-plane evidence freshness.

## 9. Readiness artifact finalization

After the preliminary readiness decision, the artifact is finalized so that its
stored values agree with the final doctor decision.

The implementation validates build, publication, latest-copy consistency,
content matching, and final readiness values.

The final validated result included:

- `READINESS_ARTIFACT_FINALIZATION_GATE=PASS`
- `FINAL_ARTIFACT_SCI_ORAN_READY_GATE=PASS`
- `FINAL_ARTIFACT_FAILURE_REASON=NONE`

## 10. Final readiness result

Two final positive doctor validation runs were retained during development:

- `/tmp/action11b.68f-doctor.out`
- `/tmp/action11b.69e-doctor.out`

Both produced the final result:

- `DOCTOR_READ_ONLY_GATE=PASS`
- `HOST_READINESS_GATE=PASS`
- `HOST_RESOURCE_READINESS_GATE=PASS`
- `CONTAINER_READINESS_GATE=PASS`
- `NETWORK_READINESS_GATE=PASS`
- `ZMQ_READINESS_GATE=PASS`
- `N2_READINESS_GATE=PASS`
- `E2_READINESS_GATE=PASS`
- `E2SM_RC_READINESS_GATE=PASS`
- `UE_SESSION_READINESS_GATE=PASS`
- `USER_PLANE_READINESS_GATE=PASS`
- `TRAFFIC_HARNESS_READINESS_GATE=PASS`
- `REPOSITORY_REPRODUCIBILITY_GATE=PASS`
- `PROCESS_CONTINUITY_GATE=PASS`
- `READINESS_ARTIFACT_GATE=PASS`
- `READINESS_FRESHNESS_GATE=PASS`
- `READINESS_ARTIFACT_FINALIZATION_GATE=PASS`
- `SCI_ORAN_READY_GATE=PASS`
- `FAILURE_REASON=NONE`

The `/tmp/action11b.*` files are temporary development evidence and are not
treated as persistent repository artifacts.

## 11. Experiment preflight integration

`scripts/experiment-harness/lib/preflight.sh` invokes
`scripts/sci-oran-doctor.sh`, reads `SCI_ORAN_READY_GATE` and
`FAILURE_REASON`, and exposes the result through the experiment preflight layer.

A positive integration test produced:

- `SCI_ORAN_PREFLIGHT_READY_GATE=PASS`
- `SCI_ORAN_PREFLIGHT_FAILURE_REASON=NONE`

Negative-path testing also demonstrated fail-closed behavior.

One validated negative case produced:

- `SCI_ORAN_PREFLIGHT_READY_GATE=FAIL`
- `SCI_ORAN_PREFLIGHT_FAILURE_REASON=USER_PLANE_READINESS_GATE`

Therefore a failed mandatory readiness condition is propagated to the experiment
preflight layer instead of being silently ignored.

## 12. Relationship to Prompt 11

Prompt 11B is a supporting infrastructure subproject for Prompt 11 Runtime
Actuator Discovery.

Prompt 11 remains paused at the Runtime Actuation Gate while the supporting
Prompt 11A, Prompt 11B, and Prompt 11C infrastructure work is completed.

Prompt 11B establishes a trustworthy readiness prerequisite for later
experiments. It does not itself discover, modify, authorize, or validate a
runtime actuator.

Therefore:

`SCI_ORAN_READY_GATE=PASS`

does not imply:

`ACTUATION_GATE=PASS`

The Runtime Actuation Gate remains a separate control point.

## 13. Completion criteria

Prompt 11B is ready for repository closure when:

1. `scripts/sci-oran-doctor.sh` contains the validated comprehensive read-only
   doctor implementation.
2. `scripts/experiment-harness/lib/preflight.sh` enforces the doctor result.
3. Positive validation demonstrates `SCI_ORAN_READY_GATE=PASS`.
4. Positive preflight validation demonstrates
   `SCI_ORAN_PREFLIGHT_READY_GATE=PASS`.
5. Negative-path testing demonstrates fail-closed propagation.
6. This canonical documentation is present.
7. `docs/roadmap/project-status.md` is synchronized.
8. The Prompt 11B change set is committed and pushed.
9. Local HEAD and remote branch HEAD are verified to match.

After these conditions are satisfied, Prompt 11B can be marked `COMPLETED`.
