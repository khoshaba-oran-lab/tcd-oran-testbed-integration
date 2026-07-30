# STATUS-CORRECTION-01

Date: 2026-07-30
Repository: `tcd-oran-testbed-integration`
Baseline commit: `f0c07abb3b30e0586967374d9a0d8e9164dcd115`

## Purpose

This record corrects the project status classification without rewriting,
deleting, or modifying the historical evidence of completed stages.

The software-only implementation remains useful and preserved. However, the
real-node gates and the final normalised schema freeze have not yet been
completed.

## Authoritative status

~~text
BASE-06G.2=CLOSED

COLLECTOR-00-SW=PASS
HW-INFO-01=PENDING
HW-CONTRACT-01=PENDING

COLLECTOR-01-SW=PASS
REAL-GATE-01=PENDING

COLLECTOR-02A-SW=PASS
COLLECTOR-02-SW=PARTIAL
REAL-GATE-02=PENDING

COLLECTOR-03-SW-PROTOTYPE=IN_PROGRESS
COLLECTOR-03-SW=NOT_ACCEPTED

NORMALISED-SCHEMA-V1=NOT_FROZEN

TEST-01=NOT_STARTED
REAL-GATE-03=NOT_STARTED
~~

## Corrections

1. The mandatory `REAL-GATE-01` has not been executed.
2. `COLLECTOR-02A-SW` passed as a narrower software-only defensive-validation
   stage.
3. Full `COLLECTOR-02-SW` remains partial.
4. `REAL-GATE-02` has not been executed.
5. The current canonical record is emulator-derived and is a draft, not a
   frozen schema v1.
6. `COLLECTOR-03-SW` was started before formal schema freeze and is therefore
   classified as a software prototype.
7. Raw and normalised outputs are not yet fully separated.
8. Experiment and software manifests are not yet implemented as accepted
   pipeline artifacts.

## Preservation rule

Completed and historical evidence bundles remain immutable. This record
supersedes only incorrect or premature status interpretations.

The current COLLECTOR-03 branch may retain prototype code, tests, and output
backend experiments, but these artifacts must not claim:

- accepted `COLLECTOR-03-SW`;
- frozen normalised schema v1;
- real-node validation;
- production compatibility guarantees.

## Required continuation order

~~text
HW-INFO-01
    ->
HW-CONTRACT-01
    ->
REAL-GATE-01
    ->
complete COLLECTOR-02-SW
    ->
REAL-GATE-02
    ->
freeze NORMALISED-SCHEMA-V1
    ->
reconcile and complete COLLECTOR-03-SW
    ->
TEST-01
    ->
REAL-GATE-03
~~

## Next active stage

~~text
NEXT_STAGE=HW-INFO-01
NEXT_STEP=OBTAIN_TESTBED_INFORMATION
~~
