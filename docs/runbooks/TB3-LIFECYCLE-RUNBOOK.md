# Sci_O-RAN Tb3 Reproducible Testbed Lifecycle Runbook

## 1. Purpose

This runbook defines the reproducible lifecycle contract implemented during
Prompt 11A for the Sci_O-RAN Tb3 testbed.

Prompt 11A provides controlled mechanisms for:

- deploy;
- teardown;
- recover;
- reset;
- day-start;
- day-stop.

The lifecycle layer is responsible for bringing the infrastructure to a known
state. It does not replace the comprehensive read-only diagnostic and readiness
verification that belongs to Prompt 11B.

A successful `DAY_START_GATE=PASS` therefore means that the lifecycle
infrastructure has converged to the canonical runtime state and can be handed
to Prompt 11B.

The readiness decision remains deferred:

~~~text
SCI_ORAN_READY_GATE=DEFERRED_TO_PROMPT_11B
PROMPT_11B_HANDOFF=REQUIRED
~~~

---

## 2. Control topology

The validated operational path is:

~~~text
homeserver
    |
    v
sci-gateway / coll.vntu.org
    |
    v
Ansible controller
    |
    v
inventory host: tb3-dell
    |
    v
target VM: tt / tb3-dell
~~~

Repository on Tb3:

~~~text
~/project/tcd-oran-testbed-integration
~~~

Validated Git branch:

~~~text
feat/tb3-dell-reproducibility
~~~

Ansible controller root:

~~~text
~/sci-oran/ansible
~~~

---

## 3. Canonical lifecycle artifacts

Core playbooks:

~~~text
ansible/playbooks/tb3-preflight.yml
ansible/playbooks/tb3-capture-state.yml
ansible/playbooks/tb3-finalize-operation.yml
ansible/playbooks/tb3-deploy.yml
ansible/playbooks/tb3-teardown.yml
ansible/playbooks/tb3-recover.yml
ansible/playbooks/tb3-reset.yml
ansible/playbooks/tb3-day-start.yml
ansible/playbooks/tb3-day-stop.yml
~~~

Operator interface:

~~~text
scripts/tb3-lifecycle.sh
~~~

Architecture document:

~~~text
docs/runbooks/TB3-LIFECYCLE-ARCHITECTURE.md
~~~

Lifecycle evidence convention:

~~~text
artifacts/lifecycle/README.md
~~~

---

## 4. Validated artifact identities

| Artifact | SHA256 |
|---|---|
| `tb3-preflight.yml` | `df731bc9dc1c7b14f5cab41a7b5f4beda65ab96779dbf01ed3b8d704a42bc84e` |
| `tb3-capture-state.yml` | `50a050fd520035068b5cca771e9759c2ba03f4b25b5089cdfa85454729ea95fc` |
| `tb3-finalize-operation.yml` | `ca4f216867e2670b13e48839e53e7fadcf241aafe2fa62b279f46898fae900fe` |
| `tb3-teardown.yml` | `2e52af6087502785554afac509578e84837f31b24fbf4f63e3d80e33340e4e36` |
| `tb3-deploy.yml` | `eae2cd9a31a0a42c4824342703f0ddc5f86b2c7568cee3444d0fbb473d91b972` |
| `tb3-recover.yml` | `18f085d200dbccf0c962f2908147d44520e95213bd520133f569d2d3df90d796` |
| `tb3-reset.yml` | `06d720c49c00d68ee4db0cddb4184ef0ab558cf502194c9d3e0a76fd2582fa11` |
| `tb3-day-start.yml` | `48afc1099bdcccf8999234841565314546d25f5efffd626bf730242f06faaf0a` |
| `tb3-day-stop.yml` | `f8cabf32d43331be390eb97408e303a27aa4b821aa3815d9b97f25409748faf6` |
| `scripts/tb3-lifecycle.sh` | `ad557fbacfa613e07027a5ddc10db7ab142bef974b9d14d418fa77c581ee1ba4` |

These identities define the validated Prompt 11A lifecycle implementation.

---

## 5. Canonical runtime contract

The controlled runtime consists of four lifecycle-owned components.

| Component | Container | IPv4 |
|---|---|---|
| 5GC | `base05_open5gs_5gc` | `10.53.1.2` |
| gNB | `base05_srsran_gnb` | `10.53.1.3` |
| UE | `base05_srsran_srsue` | `10.53.1.4` |
| Near-RT RIC | `action11_202_flexric_ric_safe` | `10.53.1.10` |

Canonical network:

~~~text
tcd-base05-zmq_ran
~~~

Validated runtime image IDs:

~~~text
5GC
sha256:e584550ebb654abcce8801c479d977f97b0397319e5dd92c1e06b7091d92160d

RIC
sha256:02a7181afaf1cb5892bbaaaeb3808e9db9bcb7594fa48396e3da56e210bc60bb

gNB
sha256:aac094264803c663fd714af28840aa9db10d323526c5e0ca6cbc22645022c292

UE
sha256:ea98a2ab87f98037bc172f8422dc1f5fc65ebad21f847bc10b5765b9ecf02410
~~~

The gNB used by the Prompt 11A lifecycle is the separately captured
E2-enabled Phase-2 runtime. The validated BASE-05 configuration is not modified
by that runtime contract.

---

## 6. Deploy

`deploy` requires a clean lifecycle-owned state and creates the canonical
runtime in the validated order:

~~~text
5GC
 |
 v
RIC
 |
 v
gNB
 |
 v
UE
~~~

A successful controlled deployment requires:

~~~text
LIFECYCLE_DEPLOY_GATE=PASS
~~~

The deploy path verifies:

- exact lifecycle configuration identities;
- exact Docker image identities;
- clean pre-deploy ownership state;
- 5GC health;
- all four running containers;
- expected network membership;
- expected lifecycle IPv4 addresses;
- persistent lifecycle evidence.

---

## 7. Teardown

`teardown` removes lifecycle-owned runtime resources in controlled order.

It does not remove the validated Docker images and does not introduce an
independent cleanup implementation for higher-level operations.

Successful teardown requires:

~~~text
LIFECYCLE_TEARDOWN_GATE=PASS
~~~

The resulting desired state is:

~~~text
base05_open5gs_5gc              ABSENT
action11_202_flexric_ric_safe   ABSENT
base05_srsran_gnb               ABSENT
base05_srsran_srsue             ABSENT
tcd-base05-zmq_ran              ABSENT
~~~

---

## 8. Redeploy

The deploy implementation was validated through a complete cycle:

~~~text
deploy
  |
  v
teardown
  |
  v
deploy
~~~

The second deployment reproduced the expected image, container, health and
network contracts.

Acceptance result:

~~~text
LIFECYCLE_REDEPLOY_GATE=PASS
~~~

---

## 9. Controlled recovery

`recover` is intended for partial, stale or inconsistent runtime state.

It deliberately reuses the existing lifecycle primitives:

~~~text
partial or stale state
        |
        v
validated teardown
        |
        v
clean state
        |
        v
validated deploy
        |
        v
canonical runtime
~~~

No second Docker cleanup mechanism is implemented in the recovery playbook.

A real recovery experiment deliberately removed the UE from an otherwise
running runtime. Recovery normalized the partial state and restored all four
components with their exact expected image IDs and network identities.

Validated recovery operation:

~~~text
lifecycle-recover-20260813T034949Z-6021438f
~~~

Acceptance result:

~~~text
CONTROLLED_RECOVERY_GATE=PASS
~~~

---

## 10. Controlled reset

`reset` performs an intentional complete reinitialization of the lifecycle
runtime.

It reuses:

~~~text
validated teardown
        |
        v
validated deploy
~~~

Validated reset operation:

~~~text
lifecycle-reset-20260813T035633Z-62826000
~~~

Acceptance result:

~~~text
CONTROLLED_RESET_GATE=PASS
~~~

---

## 11. Day-start

`day-start` is the beginning-of-day lifecycle normalization operation.

It reuses the validated recovery implementation:

~~~text
unknown, stale or current state
        |
        v
validated recovery
        |
        v
canonical infrastructure runtime
        |
        v
DAY_START_GATE=PASS
        |
        v
Prompt 11B doctor
~~~

Validated day-start operation:

~~~text
lifecycle-day-start-20260813T040609Z-cea15818
~~~

The required Prompt 11A handoff markers are:

~~~text
DAY_START_RUNTIME_NORMALIZATION_GATE=PASS
DAY_START_DEPLOY_EVIDENCE_GATE=PASS
DAY_START_GATE=PASS
SCI_ORAN_READY_GATE=DEFERRED_TO_PROMPT_11B
PROMPT_11B_HANDOFF=REQUIRED
~~~

Prompt 11A stops at this boundary. Readiness validation is performed by
Prompt 11B.

---

## 12. Day-stop

`day-stop` captures reproducibility and diagnostic evidence before controlled
teardown.

Validated sequence:

~~~text
running runtime
      |
      v
diagnostic runtime snapshot
      |
      v
snapshot checksum
      |
      v
validated teardown
      |
      v
clean stopped state
~~~

The diagnostic snapshot contains:

- repository branch and HEAD;
- `docker ps -a`;
- Compose state;
- full container inspect information;
- container PID;
- restart count;
- image ID;
- image reference;
- Docker image inspect metadata;
- bounded last 200 container log lines;
- lifecycle Docker network state.

Validated day-stop operation:

~~~text
lifecycle-day-stop-20260813T041455Z-b86ae65a
~~~

Acceptance results:

~~~text
DAY_STOP_RUNTIME_CAPTURE_GATE=PASS
DAY_STOP_EVIDENCE_GATE=PASS
DAY_STOP_TEARDOWN_GATE=PASS
DAY_STOP_CLEAN_STATE_GATE=PASS
DAY_STOP_GATE=PASS
~~~

---

## 13. Lifecycle evidence

Generated lifecycle evidence is stored under:

~~~text
artifacts/lifecycle/<operation-id>/
~~~

The normal operation bundle contains:

~~~text
before-state.txt
after-state.txt
operation.log
manifest.json
checksums.sha256
~~~

Day-stop additionally contains:

~~~text
day-stop-runtime-snapshot.txt
day-stop-runtime-snapshot.sha256
~~~

The generated operation directories are not intended for normal Git tracking.
Their schema and naming rules are defined in:

~~~text
artifacts/lifecycle/README.md
~~~

---

## 14. Idempotency and convergence

Prompt 11A treats lifecycle idempotency as convergence to the requested
runtime state.

Running-state convergence was demonstrated when `day-start` was executed from
an already running canonical runtime and again produced the canonical runtime.

Stopped-state convergence was demonstrated by reapplying `day-stop` when all
four lifecycle containers and the lifecycle network were already absent.

Validated stopped-state idempotency operation:

~~~text
lifecycle-day-stop-20260813T042013Z-ae79c532
~~~

Results:

~~~text
IDEMPOTENCY_INITIAL_CLEAN_STATE_GATE=PASS
IDEMPOTENCY_REPEAT_DAY_STOP_EXECUTION=PASS
IDEMPOTENCY_EVIDENCE_GATE=PASS
IDEMPOTENCY_FINAL_CLEAN_STATE_GATE=PASS
DAY_STOP_IDEMPOTENCY_GATE=PASS
LIFECYCLE_IDEMPOTENCY_GATE=PASS
~~~

The creation of a new evidence bundle for a repeated operation is intentional
and is not considered runtime drift.

---

## 15. Operator interface

Repository wrapper:

~~~text
scripts/tb3-lifecycle.sh
~~~

Validated controller copy:

~~~text
~/sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh
~~~

Supported operations:

~~~bash
tb3-lifecycle.sh deploy --confirm
tb3-lifecycle.sh teardown --confirm
tb3-lifecycle.sh recover --confirm
tb3-lifecycle.sh reset --confirm
tb3-lifecycle.sh day-start --confirm
tb3-lifecycle.sh day-stop --confirm
~~~

Help:

~~~bash
tb3-lifecycle.sh --help
~~~

The wrapper:

- contains no Docker lifecycle implementation;
- contains no SSH lifecycle implementation;
- delegates state changes to validated Ansible playbooks;
- requires explicit `--confirm`;
- creates a UTC-based operation ID unless an explicit valid ID is supplied.

Acceptance result:

~~~text
LIFECYCLE_OPERATOR_INTERFACE_GATE=PASS
~~~

---

## 16. Prompt 11A acceptance summary

The required lifecycle acceptance gates have been demonstrated.

| Gate | Result |
|---|---|
| `LIFECYCLE_DEPLOY_GATE` | `PASS` |
| `LIFECYCLE_TEARDOWN_GATE` | `PASS` |
| `LIFECYCLE_REDEPLOY_GATE` | `PASS` |
| `CONTROLLED_RECOVERY_GATE` | `PASS` |
| `CONTROLLED_RESET_GATE` | `PASS` |
| `DAY_START_GATE` | `PASS` |
| `DAY_STOP_GATE` | `PASS` |
| `LIFECYCLE_IDEMPOTENCY_GATE` | `PASS` |
| `LIFECYCLE_OPERATOR_INTERFACE_GATE` | `PASS` |

The functional lifecycle implementation of Prompt 11A is therefore complete.

---

## 17. Current handoff state

Following the validated day-stop and stopped-state idempotency test, the
intended current lifecycle state is:

~~~text
base05_open5gs_5gc              ABSENT
action11_202_flexric_ric_safe   ABSENT
base05_srsran_gnb               ABSENT
base05_srsran_srsue             ABSENT
tcd-base05-zmq_ran              ABSENT
~~~

This is the controlled stopped state.

The next infrastructure stage is Prompt 11B:

~~~text
Comprehensive read-only doctor
SCI_ORAN_READY_GATE
~~~

After Prompt 11B and Prompt 11C are completed, the project returns to the
paused Prompt 11 Runtime Actuation Gate.

---

## 18. Prompt boundary

Prompt 11A does not perform:

- new PRB Control experiments;
- MIN0/MAX25 xApp experiments;
- system identification;
- PID controller development;
- MPC controller development;
- new Runtime Actuation Gate experiments.

Prompt 11 remains:

~~~text
PAUSED_AT_ACTUATION_GATE
~~~

until Prompt 11A, Prompt 11B and Prompt 11C infrastructure prerequisites are
closed.

---

## 19. Operational recommendation

Normal operator usage should use the controller-side wrapper rather than
manually invoking Docker lifecycle commands.

Beginning of a work session:

~~~bash
~/sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh day-start --confirm
~~~

After successful day-start, run the Prompt 11B read-only doctor before
conducting experiments.

End of a work session:

~~~bash
~/sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh day-stop --confirm
~~~

This preserves the lifecycle evidence chain and provides a reproducible
transition between controlled running and controlled stopped states.
