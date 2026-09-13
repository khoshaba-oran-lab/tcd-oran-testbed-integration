# Sci-O-RAN recovery and experiment resumption plan

## Canonical sources

- Master plan: `docs/control/00-recovery-master-plan.md`
- Current state: `docs/control/01-current-state.md`
- Next action: `docs/control/02-next-action.md`
- Scientific design: `docs/12-siso-system-identification-design.md`
- T2 protocol: `docs/12-t2-26to39-scientific-protocol.md`

## Canonical scientific state

- T1 is closed and validated; its accepted evidence is the golden dataset.
- T2 is scientifically incomplete with one valid repetition, R03.
- The R03 scientific trigger is consumed and must never be replayed.
- R01V5 is an aborted pretrigger attempt and consumed no scientific trigger.
- No new T2 trigger and no T3-T6 transition is currently authorised.

## Stage R0 - Freeze and establish truth

Status: COMPLETE.

Experiments and runtime mutations are paused. Repository, branch, runtime,
T1 and T2 evidence boundaries have been established and published.

## Stage R1 - Repository and lifecycle consolidation

Status: COMPLETE after `RECOVERY.R1.CLOSE` passes.

The lifecycle source is integrated under `sci-oran/ansible`. Controller
paths are portable, the real inventory remains untracked, and execution
remains prohibited until controller qualification.

## Stage R2 - External controller qualification

Status: COMPLETE.


Qualification was closed by `RECOVERY.R2.CLOSE`. The active controller is
`coll.vntu.org`; it uses the canonical Git working copy and a controller-local,
Git-ignored inventory. SSH target identity and all 13 playbook syntax checks
passed. No lifecycle playbook was executed during qualification.


Confirm the controller host, repository, Ansible installation, local
inventory, SSH target and native syntax checks. This stage is read-only.

## Stage R3 - Tb3 lifecycle acceptance

Status: NOT STARTED.

Perform one controlled preflight, start, status, doctor and stop cycle.
Do not automatically recover or repeat an unknown failure.

## Stage R4 - Offline experiment qualification

Status: NOT STARTED.

Reuse the accepted T1 evidence, existing transaction validator and runner.
Require golden replay, T2 dry-run and fail-closed tests without a trigger.

## Stage R5 - Restore T2 readiness

Status: NOT STARTED.

Require platform health, user-plane smoke, telemetry, actuator path,
prospective 26-PRB readback and pre-step stationarity. No T2 trigger.

## Stage R6 - Complete T2

Status: NOT AUTHORISED.

Use a fresh transaction and run ID. Never replay R03. Permit one new
26-to-39 trigger only after every R5 gate passes.

## Stage R7 - Execute T3 through T6

Status: NOT AUTHORISED.

Use one parameterised pipeline and accept each transition separately.

## Stage R8 - Final modelling and shadow predictor

Status: NOT STARTED.

Compare models, saturation and hysteresis before qualifying ARX as a
shadow predictor. Closed-loop control requires a later decision.

## Anti-loop execution policy

- Read-only checks may be grouped into one bounded action.
- Repository changes use one checkpoint per logical result.
- Runtime and scientific actuation remain strictly one-action.
- A stage normally permits two actions and at most one repair.
- Confirmed evidence is not re-audited unless its provenance changes.
- Full logs go to evidence; chat output remains bounded.
- Only the three control documents above govern execution state.
