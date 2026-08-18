# Sci-O-RAN Lifecycle Evidence

## Purpose

This directory stores persistent operational evidence produced by the
reproducible Tb3 lifecycle automation implemented in Prompt 11A.

Lifecycle evidence is operational evidence. It is distinct from controlled
scientific experiment data stored under `datasets/` and from experiment
identity and execution metadata stored under `experiments/`.

## Identity model

Every lifecycle invocation that produces persistent evidence shall have a
unique `operation_id`.

The canonical form is:

    lifecycle-<operation>-<UTC timestamp>-<nonce>

Examples:

    lifecycle-deploy-20260812T191500Z-a13f90c2
    lifecycle-teardown-20260812T220000Z-732d54a1
    lifecycle-day-start-20260813T061500Z-8bd31ef4

The timestamp is always UTC.

The nonce exists to prevent collisions between operations started within the
same second.

Allowed operation classes initially are:

- preflight;
- snapshot;
- deploy;
- teardown;
- recover;
- day-start;
- day-stop.

`operation_id` is not an `experiment_id` and is not a `run_id`.

If a lifecycle operation is associated with a controlled scientific
experiment, `experiment_id` and `run_id` may be recorded as optional linkage
metadata, but lifecycle identity remains independent.

## Directory layout

Each retained lifecycle operation uses:

    artifacts/
      lifecycle/
        <operation_id>/
          manifest.json
          before-state.txt
          after-state.txt
          operation.log
          checksums.sha256

Additional operation-specific evidence may be stored in the same directory.

Examples include:

- Docker inspect output;
- Docker Compose state;
- network inspection;
- container logs;
- image identity records;
- recovery evidence.

## Minimum manifest contract

`manifest.json` shall identify at minimum:

- schema version;
- operation_id;
- operation type;
- UTC start timestamp;
- UTC completion timestamp;
- target host;
- repository branch;
- repository HEAD;
- operation result;
- changed components;
- lifecycle gate results;
- paths to retained before/after evidence.

Where available, it shall also record:

- container names;
- image references;
- immutable image IDs or digests;
- restart counts;
- process IDs;
- Docker network membership;
- related experiment_id;
- related run_id.

## Before and after state

State-changing lifecycle operations shall preserve both:

    before-state.txt
    after-state.txt

The before-state record must be created before the first state-changing task.

The after-state record must be created after the final state-changing or
verification task.

A failed operation must retain whatever evidence had already been captured.

Failure must not delete its evidence bundle.

## Operation log

`operation.log` contains the lifecycle execution narrative and relevant
command or Ansible task evidence.

It must not contain authentication secrets or credentials.

## Integrity

After evidence collection is complete:

    checksums.sha256

shall contain SHA256 identities for retained package files, excluding the
checksum file itself.

Evidence already finalized for an operation must not be silently rewritten.

Corrections or additional evidence require a new operation or an explicitly
documented amendment.

## Relationship to experiments

Lifecycle evidence is not automatically scientific measurement evidence.

Scientific experiments continue to use the established:

- experiment_id;
- run_id;
- dataset raw/processed/derived structure;
- experiment manifests.

A scientific run may reference a lifecycle `operation_id` when that lifecycle
operation established the runtime used by the experiment.

This preserves provenance without conflating operational automation with
scientific acquisition.

## Relationship to Prompt 11B

Prompt 11A lifecycle evidence records what lifecycle automation observed and
changed.

Prompt 11B owns comprehensive functional diagnosis and:

    SCI_ORAN_READY_GATE

A successful lifecycle operation therefore does not by itself imply full
scientific testbed readiness.
