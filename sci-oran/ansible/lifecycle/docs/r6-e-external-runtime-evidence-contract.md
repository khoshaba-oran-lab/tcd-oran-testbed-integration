# Recovery R6-E External Runtime Evidence Contract

STATUS=ACTIVE_DESIGN_CONTRACT
WORKSTREAM=R6-E_EXTERNAL_RUNTIME_EVIDENCE

## Purpose

This contract defines how Sci_O-RAN records, identifies, classifies, and
preserves references to runtime and evidence state that exists outside Git.

The repository remains the control plane.

Bulk evidence, transient runtime state, release artifacts, and historical
external data are not copied into Git merely to make them visible to the
control plane.

The purpose of this contract is to prevent undocumented local filesystem state
from silently becoming a scientific or operational dependency.

## Authority model

AUTHORITATIVE_CONTROLLER=coll.vntu.org
AUTHORITATIVE_REPOSITORY=/home/khoshaba/project/tcd-oran-testbed-integration
AUTHORITATIVE_BRANCH=main

SUBORDINATE_RUNTIME_HOST=tb3-dell

The controller repository stores lightweight metadata, policy, classification,
identity, and provenance references.

External state remains external unless a separately authorised retention,
migration, release, lifecycle, or scientific operation explicitly changes it.

## Scope

This contract applies to externally stored objects including:

- VM-local acquisition evidence;
- controller-side staging evidence;
- controller retained evidence;
- release artifacts;
- persistent operational state;
- transient runtime state;
- preserved runtime residues;
- legacy preservation roots;
- historical reproducibility evidence;
- absent historical paths that remain referenced for provenance.

## Required external-reference identity

Every repository-controlled reference to an external object must bind at least:

EXTERNAL_REFERENCE_HOST_REQUIRED=YES
EXTERNAL_REFERENCE_ABSOLUTE_PATH_REQUIRED=YES
EXTERNAL_REFERENCE_ARTIFACT_CLASS_REQUIRED=YES

Where applicable, the reference should additionally bind:

- logical object or run identity;
- experiment identity;
- operation identity;
- source repository commit;
- manifest identity;
- SHA256 identity;
- image digest or build provenance;
- retention operation identity;
- original historical absolute path.

A filesystem path alone is not sufficient identity.

## External-state classes

CLASS_A=REPOSITORY_CONTROLLED_REFERENCE
CLASS_B=PERSISTENT_EXTERNAL_OPERATIONAL_STATE
CLASS_C=VM_LOCAL_ACQUISITION_STATE
CLASS_D=AUTHORITATIVE_RETAINED_EVIDENCE
CLASS_E=DERIVED_OR_STAGING_EVIDENCE
CLASS_F=TRANSIENT_RUNTIME_STATE
CLASS_G=LEGACY_OR_HISTORICAL_EXTERNAL_STATE
CLASS_H=RETAINED_RELEASE_ARTIFACT_STATE
CLASS_I=STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT
CLASS_J=STALE_PRESERVED_RUNTIME_RESIDUE

These classes describe semantic role and must not be inferred solely from the
parent directory name.

## Known R6-E classifications

The following classifications were established during read-only discovery and
adjudication on tb3-dell:

PATH=/home/khoshaba/sci-oran-evidence
CLASSIFICATION=VM_LOCAL_ACQUISITION_STATE

PATH=/home/khoshaba/sci-oran-local-preservation
CLASSIFICATION=LEGACY_PRESERVATION_STATE

PATH=/home/khoshaba/sci-oran-release
CLASSIFICATION=RETAINED_RELEASE_ARTIFACT_STATE

PATH=/home/khoshaba/tb3-repro-evidence
CLASSIFICATION=LEGACY_REPRODUCIBILITY_EVIDENCE

PATH=/tmp/sci-oran
CLASSIFICATION=STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT

PATH=/home/khoshaba/sci-oran
CLASSIFICATION=MIXED_EXTERNAL_OPERATIONAL_STATE

PATH=/home/khoshaba/sci-oran/prompt12-runtime-684650d5aa0e8cd11d46c832f64a689b
CLASSIFICATION=STALE_PRESERVED_RUNTIME_RESIDUE

The mixed `/home/khoshaba/sci-oran` root must be classified at sub-object level
when used operationally.

## Presence is not liveness

PATH_PRESENCE_IMPLIES_RUNTIME_LIVENESS=NO
ADMISSION_METADATA_IMPLIES_RUNTIME_LIVENESS=NO
FIFO_PRESENCE_IMPLIES_RUNTIME_LIVENESS=NO

Runtime liveness requires current evidence such as:

- matching live process identity;
- process start identity where the contract requires it;
- current open-file or FIFO relationship;
- current runtime control-plane evidence;
- other explicitly defined live runtime evidence.

Historical admission metadata is provenance unless current liveness is
independently demonstrated.

For the discovered Prompt-12 preserved runtime:

ADMISSION_STATE=ADMITTED
ADMISSION_PROVIDER_PID=37415
ADMISSION_PID_LIVE=NO
FIFO_PRESENT=YES
FIFO_OPEN=NO
CLASSIFICATION=STALE_PRESERVED_RUNTIME_RESIDUE

This object must not be treated as a live actuator provider.

## Scientific evidence identity

Scientific evidence that is intended for retention must support deterministic
content identity.

SCIENTIFIC_EVIDENCE_MANIFEST_REQUIRED=YES
PREFERRED_CONTENT_IDENTITY=SHA256

Where an acquisition directory contains an existing valid manifest, that
manifest should be preserved and verified.

Where no suitable manifest exists, a separately controlled process may create a
deterministic path-relative manifest before retention.

Raw acquisition evidence must not be silently modified to manufacture
provenance.

## Acquisition versus retention

VM-local acquisition state and authoritative retained evidence are distinct.

ACQUISITION_IS_AUTHORITATIVE_RETAINED_EVIDENCE=NO

The intended flow is:

repository-controlled selection
    ->
explicit source host and source path
    ->
source qualification
    ->
deterministic source identity
    ->
R6-D verified transfer mechanism
    ->
destination verification
    ->
explicit promotion
    ->
authoritative retained evidence

The R6-D retention mechanism must be reused where applicable.

R6_D_RETENTION_REUSE_REQUIRED=YES

R6-E does not duplicate the R6-D verified transfer, verification, or promotion
logic.

## Retained evidence

Authoritative retained evidence belongs in the controller C3 retained-evidence
tier defined by R6-D.

Retained evidence must preserve:

- source host;
- source absolute path;
- source manifest identity;
- destination identity;
- transfer operation identity;
- verification outcome;
- promotion outcome;
- zero-deletion boundary.

After successful promotion, retained evidence is treated as immutable under the
R6-D storage contract.

## Release artifacts

Release artifacts are semantically distinct from retained acquisition evidence.

RELEASE_STATE_IS_RUNTIME_STATE=NO
RELEASE_STATE_IS_ACQUISITION_STATE=NO

A release may contain:

- raw evidence;
- derived evidence;
- metadata;
- schemas;
- provenance;
- checksums;
- release manifests;
- packaged archives.

The release root discovered on tb3-dell is historical release state and must
not silently become the canonical controller release tier.

Any future adoption or migration of historical release artifacts requires a
separate decision.

## Legacy and historical state

Historical external state must not be deleted, migrated, or reclassified solely
because R6-E discovers it.

LEGACY_DISCOVERY_AUTHORIZES_DELETION=NO
LEGACY_DISCOVERY_AUTHORIZES_MIGRATION=NO
LEGACY_DISCOVERY_AUTHORIZES_RETENTION=NO

Historical absolute paths should remain recorded as provenance even if physical
storage later changes.

HISTORICAL_ABSOLUTE_PATH_PRESERVATION_REQUIRED=YES

## Stale reference semantics

A repository reference to a currently absent external path is not automatically
an error.

It may represent historical provenance.

ABSENT_EXTERNAL_TARGET_CLASSIFICATION=
STALE_OR_HISTORICAL_REFERENCE_TARGET_ABSENT

A current operational workflow must never use such a path as readiness evidence
without fresh existence and semantic qualification.

## Persistent operational state

Persistent external operational state may be valid outside Git when the
contents are unsuitable for repository storage.

Such state must have repository-controlled metadata explaining:

- what it is;
- which host owns it;
- where it is;
- why it is external;
- how its identity is checked;
- whether it is required for current execution;
- whether it is recreatable;
- whether it is allowed to survive lifecycle closure.

No persistent operational state may become an implicit dependency.

## Repository registration model

R6-E registration is metadata registration, not bulk-data import.

REPOSITORY_STORES_BULK_RUNTIME_EVIDENCE=NO

A future machine-readable external-state record should be able to express:

- schema version;
- record identifier;
- host;
- absolute path;
- artifact class;
- logical role;
- existence expectation;
- liveness expectation;
- manifest path;
- manifest SHA256;
- object SHA256 when appropriate;
- Git commit;
- provenance note;
- retention state;
- original historical path;
- disposition;
- blocking classification.

## Registration safety boundary

Creating or updating an external-state reference does not authorize:

EXTERNAL_REFERENCE_AUTHORIZES_TRANSFER=NO
EXTERNAL_REFERENCE_AUTHORIZES_MIGRATION=NO
EXTERNAL_REFERENCE_AUTHORIZES_DELETION=NO
EXTERNAL_REFERENCE_AUTHORIZES_LIFECYCLE=NO
EXTERNAL_REFERENCE_AUTHORIZES_SCIENTIFIC_EXECUTION=NO
EXTERNAL_REFERENCE_AUTHORIZES_PROMPT12_TRIGGER=NO

Each consequential operation requires its own admission and authorization.

## Runtime safety invariant

A stale runtime residue must not be reused as a live runtime instance merely
because its files still exist.

STALE_RUNTIME_REUSE_WITHOUT_FRESH_ADMISSION=FORBIDDEN

Fresh runtime execution requires a future workstream-specific or
experiment-specific admission process.

R6-E itself does not start providers, open FIFOs, recreate runtime roots, deploy
Tb3, generate traffic, or issue PRB control.

## Relation to R6-F

R6-E establishes external-state identity and provenance.

R6-F Portable Experiment Runtime may later use this contract to determine which
runtime dependencies must become portable, reproducible, materializable, or
repository-controlled.

R6-E must not prematurely implement R6-F.

## Relation to R6-I

Legacy Data Catalogue remains a later workstream.

R6-E may classify legacy roots but must not expand into full historical
cataloguing.

FULL_LEGACY_CATALOGUE_CURRENTLY_AUTHORISED=NO

## Current R6-E boundary

R6_E_DISCOVERY=PASS
R6_E_CLASSIFICATION_FOR_DISCOVERED_ROOTS=PASS
R6_E_EXTERNAL_REFERENCE_CONTRACT=DEFINED

R6_E_TRANSFER_AUTHORISED=NO
R6_E_MIGRATION_AUTHORISED=NO
R6_E_DELETION_AUTHORISED=NO
R6_E_LIFECYCLE_OPERATION_AUTHORISED=NO
R6_E_SCIENTIFIC_OPERATION_AUTHORISED=NO
PROMPT12_RESUMPTION_AUTHORISED=NO

SCIENTIFIC_OPERATIONS_REMAIN_FROZEN=YES

## Next implementation responsibility

The next R6-E implementation step, if separately authorised, is to define a
minimal machine-readable external-state reference schema and a bounded
read-only validator.

That validator must verify references and classifications without performing
transfer, deletion, migration, lifecycle, or scientific actions.

NEXT_R6_E_IMPLEMENTATION=
MACHINE_READABLE_EXTERNAL_STATE_REFERENCE_SCHEMA_AND_READ_ONLY_VALIDATOR
