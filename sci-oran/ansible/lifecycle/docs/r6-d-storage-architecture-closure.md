# Recovery R6-D: Storage Architecture Closure

STATUS=PASS
R6_D=PASS
DATE=2026-09-30

## Canonical repository state

AUTHORITATIVE_CONTROLLER=coll.vntu.org
AUTHORITATIVE_REPOSITORY=/home/khoshaba/project/tcd-oran-testbed-integration
AUTHORITATIVE_BRANCH=main
IMPLEMENTATION_CHECKPOINT=8d2a5721b75c02109c068d2509480c340cde1f45

Recovery R6-D established and qualified the storage architecture required for
prospective Sci_O-RAN scientific work.

The storage design separates repository control, transient runtime state,
VM-local acquisition, authoritative retained evidence, and release/archive
storage.

## Storage tier model

The qualified storage tiers are:

C0_REPOSITORY_CONTROL_PLANE=PASS
C1_RUNTIME_EPHEMERAL_CONFIGURATION=PASS
C2_VM_LOCAL_ACQUISITION_CONFIGURATION=PASS
C3_CONTROLLER_RETAINED_EVIDENCE=PASS
C4_RELEASE_TIER_SEPARATION=PASS

The authoritative repository remains the lightweight control plane.

Runtime-generated acquisition data does not become authoritative merely by
existing on a subordinate VM.

Verified retained evidence is promoted into the controller-side C3 tier.

Release/package material remains logically separate from retained scientific
evidence.

## Canonical storage locations

Controller storage root:

/home/khoshaba/sci-oran

Controller retained-evidence root:

/home/khoshaba/sci-oran/retained-evidence

Controller release root:

/home/khoshaba/sci-oran/releases

Runtime storage root:

/home/khoshaba/sci-oran

Runtime acquisition root:

/home/khoshaba/sci-oran-evidence

The controller-side and runtime-side roles are defined through repository
configuration rather than being inferred from ad-hoc local convention.

## Evidence transfer and integrity result

R6-D qualified a controller-initiated evidence retention workflow with:

CONTROLLER_INITIATED_TRANSFER_GATE=PASS
UNIQUE_OPERATION_ID_GATE=PASS
STAGING_ISOLATION_GATE=PASS
DETERMINISTIC_SOURCE_MANIFEST_GATE=PASS
DETERMINISTIC_DESTINATION_MANIFEST_GATE=PASS
MANIFEST_EQUALITY_GATE=PASS
EXPLICIT_VERIFIED_PROMOTION_GATE=PASS
MACHINE_READABLE_OPERATION_EVIDENCE_GATE=PASS
ZERO_AUTOMATIC_SOURCE_DELETION_GATE=PASS

The implementation is repository-controlled through:

sci-oran/ansible/lifecycle/bin/sci-oran-retain-evidence.py

The verified flow is:

subordinate VM acquisition
    ->
controller-initiated bounded transfer
    ->
.incoming operation staging
    ->
independent source/destination SHA-256 verification
    ->
explicit promotion
    ->
authoritative controller retained evidence

Transfer, verification, promotion, and source deletion remain separate
responsibilities.

Source deletion is not implied by successful retention.

## First verified retained-evidence object

The first bounded real C2-to-C3 qualification completed successfully.

FIRST_VERIFIED_C3_RETAINED_OBJECT=r6-d50-first-bounded-real-transfer-v1
FIRST_VERIFIED_C3_RETAINED_PATH=/home/khoshaba/sci-oran/retained-evidence/r6-d50-first-bounded-real-transfer-v1
FIRST_VERIFIED_C3_MANIFEST_SHA256=79bf27b84603a1fdfe6584f014e836e1523b2fe3d03c8e3f8e502769801e71f6

The qualification demonstrated:

TRANSFER_GATE=PASS
INTEGRITY_VERIFICATION_GATE=PASS
MANIFEST_SEMANTIC_EQUALITY=PASS
PROMOTION_GATE=PASS
SOURCE_RETENTION_GATE=PASS

The source contained:

REGULAR_FILES=2
DIRECTORIES=1
TOTAL_REGULAR_FILE_BYTES=1518

The source remained unchanged after transfer, verification, and promotion.

## Prospective-use readiness

The acceptance condition defined by the R6-D evidence transfer and integrity
contract has been satisfied.

PROSPECTIVE_SCIENTIFIC_USE_STORAGE_READINESS=PASS

The storage architecture is therefore technically ready to support future
prospective scientific acquisition under the existing scientific admission,
lifecycle, exactly-once, evidence, and authorization rules.

This closure does not itself authorize a scientific experiment.

## Historical evidence boundary

Existing historical evidence on subordinate storage is not required to be
bulk-migrated before prospective scientific work can use the qualified storage
architecture.

HISTORICAL_BULK_MIGRATION_REQUIRED_FOR_PROSPECTIVE_USE=NO
HISTORICAL_BULK_MIGRATION_STATUS=NONBLOCKING_BACKLOG

Any future historical migration or adoption must remain separately authorized,
bounded, evidenced, and integrity-verified.

No historical bulk migration is authorized by this closure.

## Preservation rules

The following rules remain in force:

1. Raw acquisition evidence remains immutable after acquisition closure.

2. Processed and derived data must not overwrite raw evidence.

3. SHA-256 identities and provenance must be preserved.

4. Failed or partial transfer operation identifiers must not be replayed.

5. New transfers use unique operation identities.

6. A failed staged transfer is preserved for read-only adjudication unless a
   separate cleanup action is authorized.

7. Promotion is permitted only after integrity verification passes.

8. Source deletion is a separate policy decision and is not automatically
   performed.

9. Historical absolute provenance must not be rewritten merely to conform to
   the new storage topology.

10. Scientific traffic, PRB control, lifecycle execution, and evidence
    retention remain distinct control responsibilities.

## Scientific boundary

R6-D infrastructure work did not authorize new scientific experimentation.

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES

No Prompt-12 traffic generation, PRB actuation, T1-T6 reacquisition, model
fitting, or other scientific trigger is authorized by this closure.

Scientific work may resume only through a separately established authorized
successor workflow.

## Closure result

STORAGE_ARCHITECTURE_GATE=PASS
EVIDENCE_TRANSFER_INTEGRITY_GATE=PASS
PROSPECTIVE_SCIENTIFIC_USE_STORAGE_READINESS=PASS
HISTORICAL_BULK_MIGRATION_STATUS=NONBLOCKING_BACKLOG
R6_D=PASS

No authoritative successor workstream after R6-D is defined by the currently
tracked Recovery R6 plan.

NEXT_WORKSTREAM=UNRESOLVED_BY_CURRENT_AUTHORITATIVE_PLAN
