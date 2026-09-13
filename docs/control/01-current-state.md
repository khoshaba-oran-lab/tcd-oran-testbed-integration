# Sci_O-RAN current state

Updated from RECOVERY.R0.1-R0.6 evidence on 2026-09-13.

## Repository

- Working branch: `feat/prompt12-siso-identification`.
- Working HEAD: `3c3c04f593d67bdf3da67b0b3b8843f2e7d17777`.
- Worktree at the R0 boundary: clean.
- Common base with `origin/main`: `ef8936f252dc5652cfa32738613b6677b6a479b1`.
- Prompt 12 has 26 commits absent from `origin/main`.
- `origin/main` has 2 commits absent from Prompt 12.
- Changed-path overlap since the common base: zero.
- The local Prompt 12 branch is 8 commits ahead of its upstream.

## Lifecycle integration

- `origin/main` is `5f689aa221678b34ef59c12bd7db00ffc9fe84d0`.
- Lifecycle implementation commit: `3fc6308f30a1b33e7c0cac8db9429e41477470df`.
- It adds 14 files and 3095 lines under `sci-oran/ansible/`.
- Existing Prompt 12 lifecycle files remain under `ansible/` and `scripts/`.
- There is no path conflict, but there is semantic lifecycle duplication.
- Canonical integration direction: merge `origin/main` into the Prompt 12 work
  line only after the recovery-state checkpoint is preserved.
- No lifecycle namespace is deleted or declared canonical before qualification.

## Runtime boundary

- `tb3-dell` is a running Ubuntu 24.04.5 KVM guest.
- Docker is active, but no Tb3/RAN container or RAN host process is running.
- The Tb3 Docker network and `tun_srsue` are absent.
- `/tmp/gnb.log` and `/tmp/sci-oran` are absent.
- One historical stopped probe container remains; it is not active Tb3 state.
- Tb3 is stopped and experiment readiness is NO.

## Scientific boundary

- T1 13->26 is CLOSED/VALIDATED and remains the golden dataset.
- T2 R03 is the one valid estimation repetition currently recorded.
- The R03 scientific trigger was consumed and must never be replayed.
- R03 evidence remains authoritative; missing scheduler evidence must not be
  substituted from R01 or R02.
- T2 remains scientifically incomplete at one valid estimation repetition.
- The later R01V5 attempt ended ABORTED_PRETRIGGER and consumed no new trigger.
- The existing redesign handoff predates the later R01V4/R01V5 evidence and is
  historical rather than the current operational state by itself.
- A new scientific control is required to recreate the missing audit, but it is
  not authorised.
- T3-T6 are not authorised.

## Freeze

```text
EXPERIMENTS_PAUSED=YES
TB3_RUNTIME_STATE=STOPPED
T2_STATUS=INCOMPLETE_ONE_VALID_REPETITION
R03_TRIGGER_CONSUMED=YES
R03_TRIGGER_REPLAY_DECISION=NEVER_REPEAT
NEW_SCIENTIFIC_CONTROL_REQUIRED=YES
NEW_SCIENTIFIC_CONTROL_AUTHORISED=NO
T3_T6_AUTHORISED=NO
LIFECYCLE_MUTATION_AUTHORISED=NO
BRANCH_INTEGRATION_AUTHORISED=NO

## Recovery R0 checkpoint

- UPDATED_UTC=2026-09-13T14:46:16Z
- LAST_COMPLETED_ACTION=RECOVERY.R1.CLOSE
- LAST_ACTION_RESULT=PASS
- R0_STATUS=COMPLETE_AND_PUBLISHED
- WORKTREE_EXPECTED_AFTER_COMMIT=CLEAN
- RUNTIME_STATE=STOPPED
- T2_VALID_ESTIMATION_REPETITIONS=1
- R03_TRIGGER_CONSUMED=YES
- R03_TRIGGER_REPLAY_DECISION=NEVER_REPEAT
- NEW_SCIENTIFIC_CONTROL_AUTHORISED=NO
- T3_TO_T6_AUTHORISED=NO
- ORIGIN_MAIN_INTEGRATION=NOT_PERFORMED
- REMOTE_PUBLICATION=PASS_BY_RECOVERY.R0.9
- R0_PUBLICATION_UTC=2026-09-13T14:51:43Z
- R0_PUBLICATION_REMOTE=origin/feat/prompt12-siso-identification
- R0_PUBLICATION_PARENT=d1e92744917a3825eb2480bdeecb5d148f285776
- R1_INTEGRATION_UTC=2026-09-13T15:11:13Z
- R1_ORIGIN_MAIN=5f689aa221678b34ef59c12bd7db00ffc9fe84d0
- R1_SOURCE_INTEGRATION=PASS
- R1_YAML_PARSE=PASS_13_OF_13
- R1_INITIAL_ANSIBLE_SYNTAX_CHECK=UNAVAILABLE_ON_TB3_DELL
- R1_DUPLICATE_PLAYBOOKS=10
- R1_IDENTICAL_DUPLICATES=8
- R1_DIVERGENT_DUPLICATES=2
- R1_PREFLIGHT_INCOMING_BRANCH=feat/prompt12-siso-identification
- R1_RECOVER_INCOMING_GNB_IMAGE=sha256:4af028e1849c2c23848e342681d04ec1a1d2732ee25f7d41290018c93da05eb1
- PROVISIONAL_CANONICAL_LIFECYCLE_SOURCE=sci-oran/ansible
- FROZEN_LEGACY_LIFECYCLE_SOURCE=ansible/playbooks
- PORTABILITY_BLOCKER=/home/khoshaba/sci-oran/staging
- LIFECYCLE_EXECUTION_AUTHORISED=NO
- SCIENTIFIC_CONTROL_AUTHORISED=NO
- R1_PORTABILITY_UTC=2026-09-13T15:20:42Z
- R1_REPOSITORY_RELATIVE_ANSIBLE_ROOT=PASS
- R1_CONTROLLER_STAGING_PARAMETERISED=PASS
- R1_REAL_INVENTORY_POLICY=CONTROLLER_LOCAL_UNTRACKED
- R1_INVENTORY_TEMPLATE=sci-oran/ansible/inventory.ini.example
- R1_CONTROLLER_ROLE=EXTERNAL_HOST_PENDING_QUALIFICATION
- R1_MANAGED_TARGET=tb3-dell
- R1_LIFECYCLE_EXECUTION_AUTHORISED=NO
- R1_CLOSED_UTC=2026-09-13T15:39:53Z
- R0_STATUS=COMPLETE
- R1_STATUS=COMPLETE
- R1_LIFECYCLE_SOURCE=sci-oran/ansible
- R1_PORTABLE_CONTROLLER_PATHS=PASS
- R1_REAL_INVENTORY_POLICY=CONTROLLER_LOCAL_UNTRACKED
- R1_CONTROLLER_QUALIFICATION=PENDING_R2
- LIFECYCLE_EXECUTION_AUTHORISED=NO
- CURRENT_BLOCKER=EXTERNAL_CONTROLLER_NOT_QUALIFIED
