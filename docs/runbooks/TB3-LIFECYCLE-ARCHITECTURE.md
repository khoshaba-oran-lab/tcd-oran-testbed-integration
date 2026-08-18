# Sci-O-RAN Tb3 Lifecycle Architecture

## Purpose

This document defines the canonical lifecycle architecture for Prompt 11A:
Reproducible Testbed Lifecycle Automation.

The lifecycle layer is responsible for reproducibly creating, stopping,
recovering and preparing the Tb3 testbed.

Functional readiness validation belongs to Prompt 11B and is not duplicated
here.

## Control topology

The established control path is:

homeserver
-> coll.vntu.org
-> Ansible
-> tb3-dell

The Ansible controller is coll.vntu.org.

The existing controller inventory defines:

- group: sci_oran_vms;
- logical host: tb3-dell;
- SSH target: tt;
- remote user: khoshaba.

Existing gateway bundle transport and experiment execution playbooks are
retained and are not replaced by Prompt 11A.

Lifecycle orchestration itself must be implemented as repository-native
Ansible playbooks. Shell wrappers may invoke lifecycle operations but must not
contain hidden Docker orchestration logic.

The authoritative lifecycle source remains the Git repository on tb3-dell.
Until direct GitHub access from the gateway is separately established,
controller execution copies may be synchronized over the already validated
gateway-to-Tb3 path and must be identity-checked.

## Runtime ownership domains

### Domain 1: BASE-05

The validated Tb3 BASE-05 runtime is defined by the effective Compose model:

- deploy/phase-1-baseline/base-05-zmq/compose.runtime.yml;
- deploy/phase-1-baseline/base-05-zmq/compose.sandybridge.yml.

Compose project:

- tcd-base05-zmq.

Services:

- 5gc;
- gnb;
- srsue.

Network:

- tcd-base05-zmq_ran;
- subnet 10.53.1.0/24.

The generic compose.sh path is not the canonical Tb3 lifecycle path because
it does not apply the Sandy Bridge override.

### Domain 2: Near-RT RIC

Near-RT RIC is not a BASE-05 Compose service.

The currently captured Tb3 RIC contract is preserved under:

- deploy/phase-2-flexric/tb3-runtime/configs/ric.conf;
- deploy/phase-2-flexric/tb3-runtime/locks/tb3-ric-runtime.lock.

The current captured RIC uses:

- network tcd-base05-zmq_ran;
- address 10.53.1.10;
- E2 port 36421;
- E42 port 36422.

Because RIC shares the BASE-05 network, network teardown must occur only after
RIC has been stopped or removed in a controlled manner.

### Domain 3: Experimental helpers

Action11 probe containers and xApps are not members of BASE-05 Compose.

They must never be treated as implicit dependencies of the canonical baseline.

Lifecycle teardown/day-stop must identify relevant experimental helper
containers, preserve required evidence, and remove or stop only objects owned
by the Sci-O-RAN runtime policy.

## Captured Action11 state

The exact current Action11 RIC and E2-enabled gNB contracts have been preserved
before lifecycle implementation.

The following directory is historical reproducibility evidence:

- deploy/phase-2-flexric/tb3-runtime/captured-action11/

These captured files must not automatically become the canonical deployment
interface.

In particular, the validated BASE-05 gNB configuration must not be silently
replaced by the captured E2SM-RC configuration.

Promotion of an E2-enabled gNB/RIC profile into the canonical lifecycle
requires an explicit repository contract and validation.

## Lifecycle start model

The intended orchestration order is:

1. host preflight;
2. inspect existing runtime state;
3. collect before-state evidence;
4. resolve owned stale runtime objects;
5. establish the BASE-05 Docker network;
6. start 5GC;
7. wait for lifecycle-level 5GC readiness;
8. start Near-RT RIC when required by the selected validated profile;
9. start gNB;
10. wait for lifecycle-level N2/E2 handoff conditions;
11. start UE;
12. wait for UE tunnel/PDU lifecycle evidence;
13. collect after-state evidence;
14. hand off to Prompt 11B.

A container being merely "running" is not sufficient as the final
SCI_ORAN_READY_GATE. Comprehensive readiness remains the responsibility of
Prompt 11B.

## Lifecycle stop model

The intended controlled shutdown order is:

1. collect final runtime evidence;
2. stop/remove owned xApp and helper runtime objects;
3. stop UE;
4. stop gNB;
5. stop Near-RT RIC;
6. stop 5GC;
7. remove BASE-05 Compose containers;
8. remove the BASE-05 network only after external members are gone;
9. preserve configs, datasets, images and evidence.

Teardown must be idempotent.

## Recovery policy

Recovery must never be an undocumented magic restart.

Every recovery operation must record:

- failed component or violated lifecycle condition;
- recovery scope;
- component state before recovery;
- component state after recovery;
- container/image identity;
- PID before and after where meaningful;
- restart count;
- associations or lifecycle conditions restored.

Initial allowed recovery scopes are:

- UE-only;
- gNB plus UE;
- RIC;
- full controlled reset.

Additional scopes require demonstrated need.

## Daily workflow

day-start:

unknown or stale state
-> evidence
-> controlled cleanup/recovery
-> deterministic deploy
-> lifecycle handoff
-> Prompt 11B doctor

day-stop:

runtime
-> final evidence
-> runtime manifest
-> controlled teardown
-> known stopped state

## Evidence contract

Every lifecycle operation must have a unique operation ID and UTC timestamp.

Evidence must include at minimum:

- operation type;
- before state;
- after state;
- exit status;
- changed components;
- container names;
- image references;
- immutable image IDs/digests where available;
- restart counts;
- relevant network membership;
- relevant logs;
- lifecycle gate results.

Evidence must not be used as a substitute for Prompt 11B functional readiness.

## Required lifecycle playbooks

The planned repository-native Ansible interface is:

- ansible/playbooks/tb3-preflight.yml;
- ansible/playbooks/tb3-deploy.yml;
- ansible/playbooks/tb3-wait-ready.yml;
- ansible/playbooks/tb3-recover.yml;
- ansible/playbooks/tb3-teardown.yml;
- ansible/playbooks/tb3-day-start.yml;
- ansible/playbooks/tb3-day-stop.yml.

This structure is now justified by the completed lifecycle inventory and is
not a speculative repository layout.

## Acceptance gates

Prompt 11A is complete only after proving:

- LIFECYCLE_DEPLOY_GATE=PASS;
- LIFECYCLE_TEARDOWN_GATE=PASS;
- LIFECYCLE_REDEPLOY_GATE=PASS;
- CONTROLLED_RECOVERY_GATE=PASS;
- DAY_START_GATE=PASS;
- DAY_STOP_GATE=PASS;
- LIFECYCLE_IDEMPOTENCY_GATE=PASS.

The final state must be suitable for independent Prompt 11B doctor/readiness
validation.
