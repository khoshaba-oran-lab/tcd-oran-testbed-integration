# Recovery R6-D Storage Variable Implementation Contract

## 1. Purpose

This document defines the canonical configuration-variable surface for the
Recovery R6-D storage architecture.

It implements the configuration boundary defined by:

    r6-d-storage-architecture-design.md

This document does not authorize physical storage creation, evidence movement,
evidence deletion, lifecycle execution, or scientific execution.

Scientific operations remain frozen.

## 2. Configuration principles

Storage topology shall be represented in the authoritative repository.

The configuration model shall distinguish:

1. controller-side authoritative storage;
2. runtime-host local storage;
3. group-level defaults;
4. host-specific overrides.

The namespace shall use the established:

    sci_oran_*

prefix.

Storage paths shall not be encoded only in operator shell commands.

## 3. Controller-side canonical variables

The controller storage plane shall use the following canonical variables.

### 3.1 sci_oran_controller_storage_root

Semantic role:

    parent root for Sci_O-RAN controller-managed storage

Proposed initial value:

    /home/khoshaba/sci-oran

This variable describes controller-local storage only.

It shall not be interpreted as a runtime-VM path.

### 3.2 sci_oran_controller_retained_evidence_root

Semantic role:

    C3 authoritative retained scientific evidence

Proposed initial value:

    {{ sci_oran_controller_storage_root }}/retained-evidence

This is the target authoritative retention tier.

The path does not become authoritative merely because the variable exists.
Physical creation and migration require separate qualified Actions.

### 3.3 sci_oran_controller_release_root

Semantic role:

    C4 dataset release and archival packages

Proposed initial value:

    {{ sci_oran_controller_storage_root }}/releases

This root is logically distinct from retained working evidence.

### 3.4 sci_oran_controller_staging_root

Semantic role:

    controller-local transient orchestration and transfer staging

Proposed initial value:

    {{ sci_oran_controller_storage_root }}/staging

The existing controller convention:

    SCI_ORAN_STAGING_DIR

shall be treated as a compatibility surface during implementation.

A future implementation shall define precedence explicitly rather than allowing
two unrelated authoritative values.

## 4. Runtime group-level canonical variables

The runtime acquisition plane shall use the following variables.

### 4.1 sci_oran_runtime_storage_root

Semantic role:

    parent root for runtime-host Sci_O-RAN state

Proposed default:

    /home/khoshaba/sci-oran

Scope:

    sci_oran_vms group default

### 4.2 sci_oran_runtime_ephemeral_root

Semantic role:

    C1 runtime ephemeral state

Proposed default:

    {{ sci_oran_runtime_storage_root }}/runtime

Examples include:

- FIFOs;
- transient process state;
- temporary runtime logs;
- recreatable runtime material.

This root shall not become the sole retained location for accepted scientific
evidence.

### 4.3 sci_oran_runtime_acquisition_root

Semantic role:

    C2 active acquisition evidence

Proposed default:

    /home/khoshaba/sci-oran-evidence

The initial value intentionally preserves compatibility with the established
tb3-dell acquisition location.

Changing the physical location of existing evidence is not part of variable
introduction.

## 5. Runtime host-specific overrides

Host-specific configuration belongs in:

    sci-oran/ansible/host_vars/<inventory-host>.yml

A host may override:

    sci_oran_runtime_storage_root
    sci_oran_runtime_ephemeral_root
    sci_oran_runtime_acquisition_root

only when its filesystem topology requires a different value.

A host override shall not redefine controller-side roots.

For the current tb3-dell baseline, compatibility with existing paths is
preferred over premature relocation.

## 6. Variable ownership

The intended configuration ownership is:

Controller variables:

    controller-side authoritative configuration surface

Runtime defaults:

    sci-oran/ansible/group_vars/sci_oran_vms.yml

Runtime overrides:

    sci-oran/ansible/host_vars/<inventory-host>.yml

The controller configuration surface shall be introduced explicitly in a
separate implementation Action.

This contract does not silently choose an unrelated parallel mechanism.

## 7. Existing compatibility surfaces

The following existing controller conventions were discovered:

    SCI_ORAN_STAGING_DIR
    SCI_ORAN_CONTROLLER_LOG_ROOT

They shall not be removed or reinterpreted implicitly.

Implementation shall first determine whether each becomes:

1. an environment override of a canonical variable;
2. a deprecated compatibility alias;
3. a separately scoped operational path.

Any precedence rule must be explicit and fail-closed.

## 8. Existing lifecycle-local variables

Lifecycle playbooks currently define several path variables locally, including
repository and lifecycle evidence paths.

R6-D shall not perform a broad mechanical replacement of every local path
variable.

Only variables whose semantics belong to the new C1-C4 storage architecture
shall be migrated to the canonical storage configuration surface.

Repository-local lifecycle artifacts such as:

    {{ sci_oran_repo_root }}/artifacts/lifecycle

remain repository/lifecycle evidence unless separately reclassified.

## 9. Scientific-storage semantics

The storage-variable layer does not alter scientific semantics.

In particular:

- raw evidence remains immutable after acquisition closure;
- processed and derived artifacts remain provenance-linked;
- historical absolute paths remain valid historical provenance;
- existing evidence is not moved merely because a new canonical variable is
  introduced;
- rejected evidence remains distinguishable from accepted evidence;
- successful transfer never implies authorization to delete the source.

## 10. Path validation requirements

Future implementation shall validate canonical storage variables.

At minimum:

- value must be defined;
- value must be non-empty;
- value must be absolute;
- unexpected relative paths shall fail closed;
- controller variables shall not resolve through runtime-host assumptions;
- runtime variables shall be resolved for the explicitly selected inventory
  host.

Symlink and mount-point policy shall be decided separately before physical
migration.

## 11. Multi-VM behaviour

The variable model must support additional runtime VMs without modifying
playbook source for each host.

Expected resolution order for runtime variables:

    group default
        ->
    host override

No implicit all-host storage mutation is authorized.

Any future storage-management command shall retain the explicit-target model
established by Recovery R6-C.

## 12. Introduction sequence

Implementation shall proceed in bounded stages.

First:

    introduce and qualify configuration variables

Then:

    introduce read-only path qualification

Then, separately:

    create controller storage directories

Then, separately:

    qualify transfer/integrity mechanisms

Only after these stages may existing evidence migration be considered.

No migration or deletion is authorized by this contract.

## 13. Initial variable set

The canonical initial variable set is therefore:

Controller:

    sci_oran_controller_storage_root
    sci_oran_controller_retained_evidence_root
    sci_oran_controller_release_root
    sci_oran_controller_staging_root

Runtime:

    sci_oran_runtime_storage_root
    sci_oran_runtime_ephemeral_root
    sci_oran_runtime_acquisition_root

This is intentionally a minimal set.

Additional variables shall require demonstrated semantics rather than being
added speculatively.

## 14. Implementation boundary

This document authorizes no Ansible variable changes by itself.

The next implementation Action may introduce only the bounded variable surface
defined here.

It shall not:

- create controller retained-storage directories;
- move evidence;
- delete evidence;
- alter historical dataset records;
- clean Docker state;
- execute lifecycle operations;
- execute scientific operations.
