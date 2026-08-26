# Prompt 12 lifecycle auxiliary-container ownership gap — 2026-08-26

## Status

Root cause: **PROVEN**

Repair status: **NOT STARTED**

Scientific T2 R01 trigger status: **NOT CONSUMED**

## Scope

This record freezes the lifecycle defect discovered during the 2026-08-26
day-stop following the Prompt 12 T2 R01 pre-trigger session.

The defect is classified as:

`LIFECYCLE_AUXILIARY_CONTAINER_OWNERSHIP_GAP`

The record intentionally separates diagnosis from repair. No lifecycle cleanup
policy change is introduced by this freeze.

## Scientific boundary

The affected Prompt 12 scientific identity remains:

- R01 operation:
  `prompt12-t2-r01-26to39-20260825T165718Z-64af2589`
- experiment:
  `EXP-20260825-T2-26TO39-DL-18000K-R01`
- run:
  `RUN-20260825T165718Z-017`
- transition:
  `26 -> 39 PRB`

Controlled release evidence proves:

- trigger write attempts = 0;
- trigger write successes = 0;
- scientific trigger consumed = NO;
- T2 scientific trigger count = 0;
- FIFO write performed = NO;
- scientific control performed = NO.

Therefore the T2 R01 scientific trigger remains available, but the previous
blocked Action12.T2R evidence namespace must not be replayed.

## Observed lifecycle failure class

During day-stop, controlled teardown initially could not remove the BASE-05
network because a Prompt 12 auxiliary actuator remained attached to:

`tcd-base05-zmq_ran`

The remaining container was:

`prompt12-t2-r01-26to39-20260825T165718Z-64af2589`

Its frozen inspect evidence proves:

- the container was running;
- it was attached to `tcd-base05-zmq_ran`;
- `com.docker.compose.project` was absent;
- `com.docker.compose.service` was absent.

Immediately before controlled release, this was the only active network
endpoint in the frozen release evidence.

After removal of that exact container:

- active network endpoint count became 0;
- no FIFO trigger was written;
- no scientific control was performed.

The canonical day-stop retry subsequently completed successfully.

## Teardown source root cause

The affected tracked source is:

`ansible/playbooks/tb3-teardown.yml`

Frozen SHA256:

`2e52af6087502785554afac509578e84837f31b24fbf4f63e3d80e33340e4e36`

The existing implementation discovers auxiliary Action11 containers only with
the name predicate:

`^action11_`

It then removes only the resulting `sci_oran_action11_helpers`, after
excluding the active RIC identity.

This policy has two demonstrated coverage problems:

1. Prompt 12 experimental helpers such as
   `prompt12-t2-r01-26to39-...` are outside the discovery namespace.
2. historical Action11 naming drift includes names such as
   `action11r...`, which are also outside the literal `^action11_`
   predicate.

Therefore container ownership is represented by an incomplete naming
convention rather than by a complete fail-closed auxiliary-container ownership
contract.

## Root cause classification

`LIFECYCLE_AUXILIARY_CONTAINER_OWNERSHIP_GAP`

This is not a Docker engine failure and not a scientific-control failure.

It is a lifecycle ownership-policy defect: teardown can successfully remove
the explicitly known lifecycle containers but cannot reliably classify all
experiment auxiliary containers that may remain attached to the lifecycle
network.

## Repair requirements

The repair must remain fail-closed and must not become generic Docker cleanup.

Required properties:

1. Prompt 12 experiment helpers must be handled under an explicit ownership
   policy.
2. Action11 naming drift must be handled deliberately.
3. The active RIC contract must remain protected from helper classification.
4. Candidate auxiliary containers must be classified before destructive
   removal.
5. Pre-removal logs, inspect/provenance and ownership evidence must be retained.
6. Unknown containers attached to the lifecycle network must cause a
   fail-closed teardown rather than silent deletion.
7. No implementation equivalent to
   `docker rm -f $(docker ps -aq)` is permitted.
8. The repaired Git source must be validated before deployment to the separate
   canonical lifecycle installation on `coll.vntu.org`.
9. Canonical installation hashes must be verified after deployment.

## Source-to-installation boundary

Git source is maintained in:

`/home/khoshaba/project/tcd-oran-testbed-integration`

on `tb3-dell`.

The canonical lifecycle installation used from `coll.vntu.org` is:

`/home/khoshaba/sci-oran/ansible/lifecycle`

The canonical installation is a separate filesystem copy rather than the Git
working tree. Prior to repair, the canonical teardown SHA256 was verified to
match the tracked source SHA256 above.

The tracked wrapper is:

`scripts/tb3-lifecycle.sh`

and the verified pre-repair wrapper SHA256 is:

`ad557fbacfa613e07027a5ddc10db7ab142bef974b9d14d418fa77c581ee1ba4`

## Authoritative evidence

Controlled orphan release:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-r01-26to39-20260825T165718Z-64af2589-v1/day-stop-orphan-actuator-release-2026-08-26-v1`

`SHA256SUMS` SHA256:

`eaa9242704c5ddb3156f7ae274efbad71556b59005aca1fcd2eca5d787105e78`

Successful final teardown evidence:

`/home/khoshaba/project/tcd-oran-testbed-integration/artifacts/lifecycle/lifecycle-teardown-20260826T070014Z-34ae3a77`

Teardown `manifest.json` SHA256:

`454f3626472c8efa5bce035a5826d7405add942d9a0c30b2166df5a7c1bf7f56`

Teardown `checksums.sha256` SHA256:

`3812ab6cf22323c4dae7f4b6b091a9af8f9d2e22f1efedb308f9d08878ea4aad`

Repository state before this defect freeze:

- branch: `feat/prompt12-siso-identification`
- HEAD: `f394a21fb33c95247ff3f72e2cc3c1dd4cbe861f`

## Next authorised work

The next lifecycle task is to design the fail-closed auxiliary-container
ownership policy.

Fresh day-start and new T2 runtime acquisition remain **NOT AUTHORISED** until
the lifecycle repair has been implemented, validated, installed into the
canonical lifecycle copy and verified.
