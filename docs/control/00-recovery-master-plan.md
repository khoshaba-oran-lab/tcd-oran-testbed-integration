# Sci_O-RAN recovery and T2-T6 resumption plan

Status: ACTIVE

## Authority

This file defines the recovery order. `01-current-state.md` records the
accepted current state, and `02-next-action.md` limits execution to one action.
The existing Prompt 12 design, protocols, evidence and handoff records remain
the scientific sources. If these sources disagree, execution stops as BLOCKED.

## Objective

Resume T2-T6 without losing the accepted T1 result, without replaying consumed
triggers, and with Dell/VM lifecycle management incorporated reproducibly.

## Recovery order

1. R0 - freeze experiments and establish the repository/runtime baseline.
2. R1 - register T1/T2 lessons and mandatory safeguards.
3. R2 - reconcile the two lifecycle-management namespaces.
4. R3 - qualify deploy, teardown, status and doctor without scientific control.
5. R4 - replay the accepted T1 dataset offline.
6. R5 - qualify a T2 dry-run with no PRB trigger.
7. R6 - diagnose and restore user-plane readiness if required.
8. R7 - prepare one fresh T2 transaction.
9. R8 - execute a new T2 control only after all gates and explicit authority.
10. R9 - validate and close T2.
11. R10-R13 - execute and validate T3, T4, T5 and T6 sequentially.

## Permanent controls

- The repository, not chat history, is the execution source of truth.
- Exactly one bounded action is executed per cycle.
- Every action ends as PASS, FAIL or BLOCKED with evidence.
- A consumed or ambiguous trigger is never replayed.
- No scientific PRB control is implicit in this plan.
- Failed diagnostics do not automatically invoke repair.
- T3 is forbidden until T2 is closed and validated.

## R0 progress

- R0.1 repository baseline: PASS.
- R0.2 branch boundary: PASS.
- R0.3 runtime snapshot: PASS after R0.3R repair.
- R0.4 durable T1/T2 source collection: PASS.
- R0.5 historical T2 attempt adjudication: PASS.
- R0.6 integration direction decision: PASS.
- R0.7 create recovery control records: CURRENT.
- R0.8 validate and checkpoint recovery control records: PENDING.

## Recovery R0 closure

- Checkpoint action: RECOVERY.R0.8R
- Checkpoint UTC: 2026-09-13T14:46:16Z
- R0.1 through R0.6: PASS
- R0.7: FAIL before mutation
- R0.7R: PASS
- R0.8R: PASS after all checkpoint gates
- Recovery R0 status: COMPLETE LOCALLY
- Remote publication status: PUBLISHED BY RECOVERY.R0.9
- Runtime and scientific control: NOT CHANGED
