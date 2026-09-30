# Recovery R6-D Evidence Transfer and Integrity Implementation Contract

## 1. Purpose

This document defines the bounded implementation contract for verified transfer
of scientific evidence from a subordinate Sci_O-RAN runtime VM to the
controller-side retained-evidence storage plane.

It implements the R6-D storage architecture without authorising scientific
execution, source deletion, historical migration, or lifecycle changes.

## 2. Storage roles

The canonical roles are:

- C2 acquisition evidence:
  runtime-VM-local evidence produced during acquisition;
- C3 authoritative retained evidence:
  controller-side verified retained scientific evidence;
- C4 release/archive:
  publication, dataset release, and archive artifacts.

For tb3-dell the current canonical C2 source is:

    /home/khoshaba/sci-oran-evidence

The canonical controller C3 root is:

    /home/khoshaba/sci-oran/retained-evidence

C3 and C4 shall remain logically and physically distinct.

## 3. Direction of transfer

The canonical direction is:

    subordinate runtime VM
        ->
    controller retained-storage plane

The controller initiates and controls the transfer.

A runtime VM shall not independently decide where authoritative retained
evidence is stored.

## 4. Source authority

Transfer source selection shall be explicit.

The implementation shall require:

- inventory host identity;
- absolute source path;
- source existence;
- source directory type;
- source readability;
- absence of unsupported special filesystem objects;
- source object counts;
- source total byte count.

No implicit discovery of an arbitrary evidence directory is permitted.

## 5. Destination authority

The destination root shall come from the canonical controller storage
configuration:

    sci_oran_controller_retained_evidence_root

A transfer operation shall use a unique operation-specific destination below
that root.

It shall not write directly into an unrelated controller path.

## 6. Operation identity

Every real transfer shall have a unique transfer operation identifier.

An operation identifier shall never be reused for a different transfer attempt.

A failed or partial transfer remains a distinct historical operation and shall
not be silently converted into another operation.

## 7. Staging model

A real transfer shall first land in an operation-specific staging area below
the retained-evidence root.

Conceptually:

    retained-evidence/
        .incoming/
            <transfer-operation-id>/

The staging path shall not be treated as authoritative retained evidence.

Final promotion shall be a distinct step after integrity verification.

## 8. Transfer mechanism

The initial implementation shall use controller-initiated rsync over the
already-qualified SSH path.

Required properties:

- archive semantics;
- no --delete;
- no source-side deletion;
- no implicit overwrite of an existing completed retained operation;
- explicit source and destination paths;
- explicit inventory-resolved runtime identity;
- fail-closed exit handling.

The transfer implementation shall not depend on an unrecorded interactive shell
command.

## 9. Source snapshot identity

Immediately before transfer, the implementation shall record at least:

- source host identity;
- source root;
- UTC timestamp;
- regular-file count;
- directory count;
- total byte count;
- source manifest SHA-256 identity.

The source manifest shall contain deterministic path-relative SHA-256 records
for regular files.

Manifest generation shall not alter source evidence.

## 10. Destination integrity

After rsync completion, the destination staging tree shall be independently
verified.

Verification shall establish at least:

- expected regular-file count;
- expected directory count;
- expected total byte count;
- deterministic destination SHA-256 manifest;
- equality of source and destination file identities.

A successful rsync exit code alone is insufficient evidence of integrity.

## 11. Manifest comparison

Source and destination manifests shall use the same normalized relative-path
representation.

The implementation shall fail closed if:

- a source file is absent at destination;
- an unexpected destination regular file exists;
- any SHA-256 digest differs;
- the manifest cardinalities differ;
- normalization produces duplicate relative paths.

## 12. Promotion boundary

Verified staging data may become authoritative C3 evidence only after all
integrity gates pass.

Promotion shall be explicit.

The implementation shall not silently merge a staging tree into an already
existing authoritative operation directory.

An existing final destination is a fail-closed collision unless a separate
adoption policy explicitly permits otherwise.

## 13. Immutability boundary

After successful promotion, authoritative retained evidence shall be treated as
immutable scientific evidence.

Subsequent corrections shall create a new retained artifact or operation rather
than editing accepted raw evidence in place.

## 14. Source deletion policy

Successful transfer does not authorise deletion.

Successful integrity verification does not authorise deletion.

Successful promotion does not authorise deletion.

Source evidence shall remain intact unless a separate future Action explicitly
defines and authorises source-retention or deletion policy.

The initial implementation shall contain no automatic source deletion path.

## 15. Historical migration boundary

The approximately 19 GB currently present below:

    /home/khoshaba/sci-oran-evidence

constitutes historical existing evidence.

Qualification of the transfer mechanism does not itself authorise migration of
that historical tree.

Historical migration shall be a separately authorised operation with its own
operation identity and evidence manifest.

## 16. Prospective use

Once the transfer/integrity mechanism is implemented and qualified, it may be
used prospectively for future closed scientific acquisitions.

New scientific acquisition shall not rely indefinitely on the runtime VM as
the sole retained copy of accepted evidence.

## 17. Repository implementation surface

The canonical implementation shall live under the existing lifecycle control
plane rather than the scientific experiment harness.

Expected implementation surfaces are:

    sci-oran/ansible/lifecycle/bin/
    sci-oran/ansible/lifecycle/playbooks/

The experiment-harness directory shall not become the controller storage
orchestration layer.

## 18. Separation from scientific execution

The transfer implementation shall not:

- generate scientific traffic;
- alter PRB settings;
- start or stop scientific experiments;
- replay scientific triggers;
- alter acquisition contents;
- execute Tb3 lifecycle deploy/teardown implicitly.

Storage retention is a separate operational responsibility.

## 19. Dry-run requirement

Before every newly introduced real transfer mode is accepted, a dry-run shall
demonstrate:

- correct source host;
- correct source root;
- correct destination root;
- no delete plan;
- expected object cardinality;
- no destination mutation.

The R6-D D35 qualification establishes this property for the current Tb3
source/destination path.

## 20. Failure semantics

Any failure after destination staging begins shall preserve the failed staging
operation for adjudication unless a separately authorised cleanup Action
removes it.

A failed transfer shall not be automatically retried under the same operation
identifier.

After partial mutation followed by error, the next Action shall be read-only
forensics.

## 21. Evidence of transfer operation

Each real transfer operation shall retain machine-readable evidence including
at least:

- operation identifier;
- source host;
- source path;
- destination staging path;
- final destination path;
- start and completion UTC timestamps;
- rsync result;
- source object counts and byte count;
- destination object counts and byte count;
- source manifest identity;
- destination manifest identity;
- manifest comparison result;
- promotion result;
- source-deletion-performed = NO for the initial implementation.

## 22. Multi-VM requirement

The implementation shall not hard-code tb3-dell as the only possible runtime
VM.

Runtime identity shall be supplied from canonical inventory and host/group
variables.

Per-host source-root overrides may be used only through the established
storage-variable hierarchy.

## 23. Initial implementation exclusions

The first implementation shall not include:

- automatic historical migration;
- automatic deletion;
- compression;
- deduplication;
- remote object storage;
- cloud archival;
- release packaging;
- Docker cleanup;
- scientific orchestration.

These responsibilities remain outside the initial bounded transfer mechanism.

## 24. Implementation sequence

Implementation shall proceed in bounded steps:

1. define the transfer/integrity implementation contract;
2. qualify the contract;
3. commit and publish the contract;
4. implement the bounded transfer mechanism;
5. qualify dry-run behavior from the repository implementation;
6. qualify manifest generation and comparison;
7. perform one separately authorised real transfer;
8. verify destination integrity;
9. promote only after integrity PASS;
10. separately decide historical migration/adoption policy.

No step authorises source deletion.

## 25. Initial R6-D acceptance condition

The transfer/integrity workstream is technically ready for prospective
scientific use when all of the following are demonstrated:

- repository-controlled transfer implementation;
- controller-driven source selection;
- unique operation identity;
- staging isolation;
- deterministic SHA-256 source manifest;
- deterministic SHA-256 destination manifest;
- manifest equality;
- explicit verified promotion;
- retained machine-readable transfer evidence;
- zero automatic source deletion.

Historical evidence migration is not required to satisfy this prospective-use
condition.
