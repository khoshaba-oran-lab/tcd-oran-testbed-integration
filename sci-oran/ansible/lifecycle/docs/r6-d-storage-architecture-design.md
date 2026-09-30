# Recovery R6-D Storage Architecture Design Contract

## 1. Status

This document defines the target storage architecture for Recovery R6-D:
Centralized, Reproducible and Scalable O-RAN Experiment Platform.

It is an architecture contract only.

It does not authorize:

- scientific traffic;
- PRB control;
- Prompt-12 T1-T6 execution;
- lifecycle execution;
- evidence deletion;
- evidence migration;
- Docker cleanup;
- filesystem creation outside the repository;
- modification of existing scientific evidence.

Scientific operations remain frozen.

## 2. Architectural context

The Sci_O-RAN platform has two principal roles.

Controller:

    coll.vntu.org

Runtime VM:

    tb3-dell

The authoritative repository is:

    /home/khoshaba/project/tcd-oran-testbed-integration

The canonical branch is:

    main

The controller is the authoritative control centre.

Runtime VMs are subordinate execution targets and shall not become independent
control centres.

## 3. Established storage baseline

### 3.1 Controller

Observed during Recovery R6-D:

- `/home` is an XFS filesystem on `/dev/mapper/cs-home`;
- total capacity: approximately 856 GiB;
- free capacity during discovery: approximately 589 GiB;
- `/home/khoshaba/sci-oran` exists;
- it is not a separate mount point;
- current controller Sci_O-RAN operational state is small;
- `/home/khoshaba/sci-oran-evidence` does not currently exist.

### 3.2 tb3-dell

Observed during Recovery R6-D:

- root and home data reside on `/dev/vda1`;
- filesystem: ext4;
- total filesystem capacity: approximately 96 GiB;
- free capacity during discovery: approximately 62 GiB;
- `/home/khoshaba/sci-oran` occupies approximately 182 MiB;
- `/home/khoshaba/sci-oran-evidence` occupies approximately 19 GiB;
- Docker uses the same physical filesystem;
- Docker images occupy several GiB;
- Docker build cache also occupies several GiB.

Therefore scientific evidence, runtime/build state, and Docker storage currently
compete for the same comparatively small runtime-VM filesystem.

This is not the target scalable architecture.

## 4. Existing scientific data contract

R6-D shall preserve the existing Sci_O-RAN scientific semantics.

The canonical scientific transformation hierarchy is:

    raw -> processed -> derived

The following invariants are retained:

1. raw scientific evidence is immutable after acquisition closure;
2. processed and derived artifacts shall not overwrite raw evidence;
3. processed and derived artifacts shall remain traceable to their raw inputs;
4. retained scientific artifacts shall have integrity identities;
5. SHA-256 is the established integrity algorithm;
6. experiment, run, and artifact identities shall remain explicit;
7. failed or rejected runs may retain evidence without becoming accepted
   scientific evidence;
8. a later run shall not reuse or overwrite an earlier run's raw namespace;
9. dataset release/versioning does not authorize modification of immutable raw
   evidence.

R6-D changes physical placement and lifecycle responsibility only.

It does not redefine these scientific semantics.

## 5. Storage-plane separation

The target architecture defines five logical storage classes.

### 5.1 Class C0 — Repository control plane

Purpose:

- Ansible;
- lifecycle code;
- experiment orchestration code;
- schemas;
- manifests;
- lightweight dataset metadata;
- checksums;
- provenance references;
- storage policy;
- host and group configuration.

Authority:

    authoritative Git repository on coll.vntu.org

GitHub remains the remote source-distribution and checkpoint mechanism.

Heavy scientific payload shall not be added to Git merely to obtain centralized
storage.

### 5.2 Class C1 — Runtime ephemeral state

Purpose:

- process runtime state;
- FIFOs;
- transient logs;
- caches;
- temporary staging;
- build workspace;
- generated runtime state that can be recreated.

Primary location:

    subordinate runtime VM

Properties:

- VM-local;
- bounded;
- non-authoritative after the operation requiring it has closed;
- eligible for future policy-controlled cleanup;
- never the sole retained copy of accepted scientific evidence.

Examples from the current system include runtime roots under:

    /home/khoshaba/sci-oran/

The exact future root shall be parameterized rather than assumed globally.

### 5.3 Class C2 — Acquisition evidence

Purpose:

- evidence written during an active experiment or operational evidence-producing
  action.

Primary acquisition location:

    subordinate runtime VM

Reason:

Acquisition shall not depend on synchronous remote storage availability in the
critical measurement path unless a future experiment contract explicitly
requires and validates such behaviour.

Properties:

- run-scoped;
- experiment-scoped where applicable;
- locally writable during acquisition;
- closed after acquisition completion;
- immutable after closure when classified as raw scientific evidence.

C2 is a working acquisition tier, not the final authoritative retention tier.

### 5.4 Class C3 — Authoritative retained evidence

Purpose:

- closed raw evidence;
- retained processed artifacts;
- retained derived artifacts;
- evidence manifests;
- evidence checksums;
- provenance necessary to reproduce or audit scientific claims;
- retained rejected/failed evidence where policy requires preservation.

Target authority:

    coll.vntu.org

The controller shall become the authoritative retained-storage plane.

A runtime VM shall not remain the only authoritative holder of closed scientific
evidence.

The final physical path shall be parameterized through the authoritative
repository before any migration occurs.

### 5.5 Class C4 — Dataset release and archival package

Purpose:

- versioned dataset packages;
- publication-ready raw/processed/derived selection;
- metadata;
- schemas;
- release manifests;
- licenses;
- SHA-256 manifests;
- archival/publication references.

Target authority:

    coll.vntu.org

Release storage is logically distinct from working acquisition evidence.

Existing examples such as:

    DS-20260817-001-r03-prb-actuation-v1.0.0

demonstrate the required package semantics.

Publication to an external archive is a separate explicit operation and is not
implicit in C4.

## 6. Reproducibility artifacts

Scientific reproducibility includes more than measurement files.

The storage model shall preserve references to or retained copies of artifacts
that cannot be safely reconstructed, including where applicable:

- exact Docker image digests;
- archival Docker images;
- immutable base-image dependencies;
- configuration hashes;
- source revisions;
- build provenance;
- software manifests.

The preferred reproducibility chain remains:

    Git commit
      -> Dockerfile
      -> pinned source/base image
      -> controlled build procedure
      -> immutable image digest

Where exact reconstruction is not established, an immutable validated runtime
artifact may require preservation.

R6-D shall not delete Docker images or archives solely because corresponding
Dockerfiles exist.

## 7. Existing non-canonical roots

The following tb3-dell roots were discovered:

    /home/khoshaba/sci-oran-local-preservation
    /home/khoshaba/sci-oran-release
    /home/khoshaba/tb3-repro-evidence

Their observed roles are:

- `sci-oran-local-preservation`:
  historical preservation/offload control records;

- `sci-oran-release`:
  historical dataset release/package area;

- `tb3-repro-evidence`:
  historical reproducibility and runtime-qualification evidence.

These roots are not currently parameterized by the authoritative repository.

They shall not be deleted, renamed, merged, or migrated merely because R6-D
defines a new target architecture.

They require explicit inventory and migration/adoption decisions.

## 8. Physical-placement principle

The target topology is:

    authoritative Git control plane
            |
            v
      coll.vntu.org
    retained storage plane
            ^
            |
      verified transfer
            |
      subordinate VM
    acquisition/runtime plane

The controller provides centralized retention.

The runtime VM provides locality for active acquisition.

This separation prevents:

- scientific evidence from depending permanently on a small runtime disk;
- runtime Docker/build growth from competing indefinitely with retained
  scientific evidence;
- future additional Tb3-class VMs from inventing independent storage layouts;
- evidence location from being encoded only in operator memory.

## 9. Multi-VM scalability

Storage configuration shall be parameterized through the authoritative
repository.

Future runtime hosts may differ in:

- local acquisition root;
- local runtime root;
- local capacity;
- retained-evidence transfer source.

The controller-side retained-storage policy shall remain common where possible.

No implementation shall assume that `tb3-dell` is the only future runtime host.

Storage variables shall therefore distinguish:

- controller-side authoritative roots;
- group-level runtime defaults;
- host-specific overrides.

## 10. Migration safety contract

Existing evidence migration is a separate future operation.

No source evidence may be deleted merely because a destination copy exists.

A future migration shall be fail-closed and shall require at least:

1. explicit source root;
2. explicit destination root;
3. source inventory;
4. source byte/file accounting where practical;
5. SHA-256 identity for retained artifacts or equivalent manifest coverage;
6. transfer result;
7. destination verification;
8. independent source-versus-destination adjudication;
9. retained migration manifest;
10. explicit authorization before any source deletion.

Copying and deleting are separate operations.

Successful copy shall never automatically authorize deletion.

Existing scientific evidence shall remain untouched until migration policy and
implementation are separately qualified.

## 11. Runtime-disk protection

The current tb3-dell runtime disk is finite and shared by:

- operating-system state;
- Docker;
- builds;
- runtime state;
- scientific acquisition;
- historical retained evidence.

The future implementation shall therefore support capacity gates.

At minimum the policy shall eventually define:

- admission free-space threshold;
- warning threshold;
- critical threshold;
- behaviour when the threshold is not satisfied.

A scientific run shall not begin merely because the filesystem is technically
writable.

The precise thresholds are not defined by this design document and require a
separate bounded policy decision.

## 12. Path parameterization requirement

Future R6-D implementation shall not embed the new physical storage topology
only in shell commands or operator documentation.

Canonical paths shall be represented in the authoritative repository.

Expected configuration layers are:

    sci-oran/ansible/group_vars/sci_oran_vms.yml
    sci-oran/ansible/host_vars/<runtime-host>.yml

and, where controller-specific configuration is required, an explicit
controller-side configuration surface.

The exact variable names and paths require a separate implementation contract.

## 13. Compatibility requirement

Existing historical absolute paths remain valid evidence provenance.

R6-D shall not rewrite historical manifests solely to make them resemble the
new architecture.

Historical provenance describes where evidence actually existed.

New storage policy applies prospectively unless a separately verified migration
creates an additional authoritative retained copy.

## 14. Current R6-D implementation boundary

This architecture contract authorizes no physical storage changes.

The next implementation work must separately define:

- canonical storage variables;
- canonical controller retained-storage roots;
- runtime acquisition/runtime roots;
- directory ownership and permissions;
- transfer mechanism;
- integrity verification mechanism;
- capacity gates;
- migration/adoption rules for existing data;
- lifecycle integration boundaries.

Each consequential mutation remains subject to the ONE-ACTION-AT-A-TIME
protocol.

## 15. Architectural decision

Recovery R6-D adopts the following model:

    Centralized retained storage
    + VM-local bounded acquisition
    + immutable scientific evidence
    + Git-based storage policy and metadata
    + explicit verified transfer
    + no implicit source deletion
    + host-parameterized multi-VM paths

This model extends the already established Sci_O-RAN dataset and reproducibility
contracts without replacing their scientific semantics.
