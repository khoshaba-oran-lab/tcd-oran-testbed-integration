# Phase F.F03 — single T2 EXPERIMENT source candidate

Status: **SOURCE-ONLY ENGINEERING CANDIDATE. NOT ADMITTED FOR LIVE USE.**
All code in this package is based on the published Phase C scientific
checkpoint `865815863846022ab37590407b18ed822fdffe36` plus the
operator-exported canonical smoke/Doctor/policy sources. Git commit, Git
push, Day-Start, Day-Stop and real PRB/traffic operations are out of scope.

## The three operator macrooperations

1. Canonical `DAY-START` from `coll.vntu.org`, separately authorised.
2. Exactly one controller-side `EXPERIMENT` from `coll.vntu.org` with one
   run-scoped ID and full combined authorisation for (a) one diagnostic
   smoke, (b) one live Doctor, (c) one persistent provider, (d) exactly one
   initial26 non-scientific PRB request and its authoritative readback,
   (e) one scientific T2 26->39 PRB FIFO trigger and UDP DL 180s traffic,
   and (f) evidence adjudication. No lifecycle operation in this macro.
3. Canonical `DAY-STOP`, independently authorised even after failure.

Before any real experiment the operator must have the same approved commit
on the controller and runtime host. The controller requires an installed
inventory (`SCI_ORAN_INVENTORY`, or the standard
`sci-oran/ansible/inventory.ini`), which is intentionally NOT bundled as a
public or synthetic inventory. No `ansible-playbook` compilation/execution
has yet been performed on the actual controller for this F03 candidate.

## Existing tools reused without semantic changes

- `prompt12-production-provider-launch-materializer.py`,
  `prompt12-production-provider-manager-launcher.py`,
  `prompt12-persistent-prearmed-actuator-provider.py` and the portable
  runtime preflight supply a nonrestarting, prearmed provider.
- `prompt12-bounded-runtime-profile-materializer.py`,
  `prompt12-bounded-production-binding-builder.py`,
  `prompt12-resume-precontrol-materializer.py` and
  `prompt12-resume-single-transition-materializer.py` create fresh
  run-scoped input artifacts.
- `prompt12-initial26-preconditioning.yml` provides a separate,
  non-scientific 275->26 PRB preconditioning step with exactly-once
  wrapper evidence and authoritative readback. It is NOT an additional
  scientific T2 transition, but it IS a real PRB-changing action and must
  be covered by explicit live authorisation.
- `prompt12-resume-single-transition.yml` owns the scientific 26->39
  transition. Its existing 26s prephase, <=800ms freshness, 180s
  offered UDP traffic and >=10s postphase gates remain unchanged.
- Canonical `sci-oran-user-plane-smoke.sh` and `sci-oran-doctor.sh` are
  bound into one order-preserving readiness operation after UE tunnel
  stabilisation. Never run Doctor first and treat missing smoke evidence
  as an unexpected RAN failure.

## New components

- `prompt12-t2-prearm-plan.py`: exclusively records allocation and
  deterministic future ratio-binding filenames BEFORE the provider is
  launched. Reader remains separate from trigger execution.
- `prompt12-t2-input-assembler.py`: binds new RUN, portable runtime
  admission, prearmed FIFO, profile, manifest and resume inputs. The
  scientific T2 playbook itself creates `t2-single-transition.json` in
  live mode; it is NOT pre-created.
- `prompt12-t2-readiness-sequence.py`: one smoke then Doctor with
  exclusive intent/outcome/failure evidence; no retries.
- `prompt12-t2-experiment.py`: one controller macro with target,
  explicit authorisation and irreversible run-ID claim (including
  cross-experiment reuse protection). `--mode offline-qualify` invokes
  nonexecuting tests; it does not run Ansible. `--mode live` is
  disallowed until separately authorised after qualification.
- `prompt12-t2-experiment.yml`: sequence with exact host and Git gates,
  provider materialisation, one initial26, one T2 and independent
  adjudication. Does not call lifecycle wrapper, resets or T3-T6.
- `prompt12-t2-evidence-adjudicator.py`: checks existing 26-PRB
  evidence, precontrol stationarity, one FIFO trigger, real 39-PRB
  readback, post-stationarity, all scientific JSONL rows against
  schema, interval coverage/continuity and the three actuator events.
  It does not collect or synthesise scientific evidence in live mode.

## Diagnostic TTL versus scientific freshness

`user-plane-readiness.policy` changes the diagnostic smoke evidence
TTL from 300s to 1800s. Doctor's final readiness-artifact check reads
this value from the SAME policy rather than retaining a hardcoded 300s.
The runtime identity, epoch/freshness ordering and user-plane fingerprint
checks remain mandatory. This is not the scientific freshness gate;
the 800ms age limit immediately before scientific FIFO trigger remains
strictly unchanged.

## Offline qualification and remaining gates

The synthetic end-to-end test invokes REAL provider launch/materialisation
contracts, actual production materializers, real schema validation and
source playbook structure checks. Smoke, Doctor, provider runtime,
initial26 response, UDP traffic and scientific readback are explicitly
SYNTHETIC in these offline tests. No live packets/FIFO writes/Docker or
lifecycle operations have been generated.

**Live GO is NOT established** by these tests. Additional mandatory
admission steps include:

- Native `ansible-playbook --syntax-check` of the complete imported F03
  playbook on the controller with its installed Ansible version;
- verification that all required deployed paths, prearmed manager
  admission, qualified production Python venv and inventory are valid;
- fail-closed dry-run/inspection of the assembled operator command and
  science parameters on the actual synchronized Git head;
- separate explicit consent for two PRB requests (initial26 and T2),
  diagnostic smoke, bounded UDP traffic, FIFO trigger and evidence;
- independent scientific review of *real*, never synthetic, run data.

An Ansible failure after provider startup may leave persistent provider
resources/evidence for operator adjudication. They MUST NOT be silently
removed or replayed; canonical Day-Stop is separately authorised.
No automatic retry of user-plane smoke, initial26, traffic, FIFO or T2.
