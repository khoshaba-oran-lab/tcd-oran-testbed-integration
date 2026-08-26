# Prompt 12 lifecycle auxiliary-container ownership repair design

## Status

Design status: **FROZEN FOR IMPLEMENTATION**

Implementation status: **NOT STARTED**

Deployment status: **NOT STARTED**

Fresh day-start: **NOT AUTHORISED**

## Purpose

This design repairs the proven:

`LIFECYCLE_AUXILIARY_CONTAINER_OWNERSHIP_GAP`

without converting teardown into generic Docker cleanup.

The repair applies to:

`ansible/playbooks/tb3-teardown.yml`

and preserves the existing controlled lifecycle model.

## Safety model

The teardown policy shall be fail-closed.

No container may become removable merely because it exists in Docker.

A container must belong to one of the explicitly defined lifecycle classes.

The controlled BASE-05 network remains:

`tcd-base05-zmq_ran`

## Container classes

Every container attached to the controlled BASE-05 network must classify into
exactly one of the following classes before destructive cleanup begins.

### 1. Canonical core containers

Exact identities:

- `base05_open5gs_5gc`
- `base05_srsran_gnb`
- `base05_srsran_srsue`

These remain managed by the existing dedicated teardown tasks.

### 2. Active RIC contract

The active RIC identity continues to be resolved from:

`deploy/phase-2-flexric/tb3-runtime/locks/tb3-ric-runtime.lock`

The exact resolved container name is protected from auxiliary-helper
classification even if its name also matches a legacy Action11 namespace.

The active RIC remains managed only by the existing dedicated RIC teardown
path.

### 3. Explicit lifecycle-owned auxiliary helpers

For compatibility with already demonstrated experiment tooling, an auxiliary
container is lifecycle-owned by name only when its complete Docker name
matches the anchored extended regular expression:

`^(action11_|action11r|prompt12[-_])[A-Za-z0-9][A-Za-z0-9_.-]*$`

This deliberately covers:

- historical `action11_...` helpers;
- observed Action11 naming drift such as `action11r...`;
- Prompt 12 experiment helpers such as `prompt12-t2-r01-...`.

The exact active RIC identity is excluded after this discovery.

The regular expression is an explicit ownership namespace. It must not be
broadened to generic substrings such as `action`, `prompt`, `oran`, `ric`,
`xapp`, or arbitrary containers attached to the network.

### 4. Unknown attached containers

Any container attached to `tcd-base05-zmq_ran` that is not:

- one of the three exact core identities;
- the exact active RIC identity; or
- an explicitly owned auxiliary helper;

is classified as:

`UNKNOWN_NETWORK_CONTAINER`

Presence of one or more unknown attached containers must fail the ownership
admission gate **before any destructive removal task is executed**.

Unknown containers must never be silently removed.

## Discovery model

The implementation shall perform two bounded discoveries.

### Global auxiliary discovery

Use `docker ps -a --format` to obtain container names and select only names
matching the exact auxiliary ownership regular expression.

This preserves cleanup of lifecycle-owned historical helpers even if they are
not currently attached to the BASE-05 network.

### Controlled-network membership discovery

Inspect only:

`tcd-base05-zmq_ran`

and obtain the names of containers currently attached to that network.

If the network is already absent, network membership is the empty set.

Every discovered network member must then pass the classification model above.

## Ordering invariant

Before removal of any auxiliary, UE, gNB, RIC, 5GC, or network resource, the
playbook shall establish:

`AUXILIARY_OWNERSHIP_ADMISSION_GATE=PASS`

This requires:

1. active RIC identity resolved;
2. explicit auxiliary candidates discovered;
3. controlled-network membership captured;
4. every attached network member classified;
5. unknown attached container count equal to zero.

Failure of this gate must abort destructive teardown.

## Evidence required before auxiliary removal

For every lifecycle-owned auxiliary helper selected for removal, preserve:

1. complete `docker inspect` JSON;
2. bounded timestamped Docker logs;
3. container name;
4. container ID;
5. image ID;
6. configured image reference;
7. running/status state;
8. attached network identities;
9. Docker Compose project/service labels when present.

Evidence shall be written under the current lifecycle operation directory:

`artifacts/lifecycle/<operation_id>/`

before the corresponding `docker rm -f`.

The implementation must use filesystem-safe deterministic filenames derived
from the already validated Docker container name.

## Ownership evidence

The operation directory shall also retain a textual ownership classification
record containing, at minimum:

- active RIC identity;
- auxiliary ownership regular expression;
- discovered lifecycle-owned auxiliary helper names;
- controlled-network member names;
- unknown network member names;
- unknown network member count;
- ownership admission result.

This record is evidence of why each auxiliary container was eligible for
destructive cleanup.

## Auxiliary removal

Only the list produced by the explicit auxiliary ownership classification may
be passed to:

`docker rm -f`

No command may construct the removal list from all Docker containers.

The following patterns are explicitly prohibited:

`docker rm -f $(docker ps -aq)`

and any semantic equivalent.

## Final clean-state validation

The existing final validation must be updated so that naming drift cannot
escape the clean-state gate.

After controlled teardown:

1. the three canonical core containers must be absent;
2. the active RIC container must be absent;
3. no container whose complete name matches the frozen auxiliary ownership
   regular expression may remain;
4. `tcd-base05-zmq_ran` must be absent.

The legacy final check based only on `^action11_` is insufficient.

## Active RIC protection invariant

The exact RIC identity from the runtime lock must never be included in the
auxiliary removal list.

The implementation shall assert this explicitly before auxiliary removals.

This invariant is required because the current active RIC name itself belongs
to the historical `action11_...` namespace.

## Prompt 12 scientific boundary

This lifecycle repair does not authorise or execute any Prompt 12 scientific
control.

For the preserved T2 R01:

- trigger write attempts remain 0;
- trigger write successes remain 0;
- scientific trigger consumed remains NO;
- T2 scientific trigger count remains 0.

No FIFO trigger is part of lifecycle repair validation.

## Validation requirements before canonical deployment

The Git implementation must pass, at minimum:

1. YAML syntax validation;
2. Ansible syntax check where available;
3. source inspection proving no generic Docker cleanup;
4. explicit regex fixture tests for accepted names:
   - `action11_202_flexric_ric_safe`
   - `action11r50ab-prb25-actuator-r03`
   - `action11r44-prb25-actuator-r02`
   - `prompt12-t2-r01-26to39-example`
5. explicit regex fixture tests rejecting unrelated names;
6. active-RIC exclusion test;
7. unknown-network-container fail-closed test;
8. evidence-path/provenance validation;
9. final clean-state predicate validation.

Live destructive validation is not authorised until offline/source validation
passes.

## Git to canonical installation boundary

Authoritative Git source is maintained on `tb3-dell`.

Operational lifecycle execution uses the separate canonical installation on
`coll.vntu.org`:

`/home/khoshaba/sci-oran/ansible/lifecycle`

The implementation must first be validated and checkpointed in Git.

Only then may the exact validated lifecycle source be installed into the
canonical copy.

Post-installation SHA256 parity is mandatory.

## Next authorised work

After this design is frozen, the next authorised task is:

`IMPLEMENT_LIFECYCLE_AUXILIARY_OWNERSHIP_REPAIR_IN_GIT_SOURCE`

Fresh day-start remains prohibited until implementation, offline validation,
canonical installation, and post-installation verification all pass.
