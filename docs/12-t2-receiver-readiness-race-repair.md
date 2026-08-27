# Prompt 12 T2 receiver readiness race repair

## Scope

This record freezes the pre-trigger workload-start failure observed while
preparing the replacement T2 logical R01 estimation repetition and the
subsequent repair validation.

The scientific transition itself was never triggered.

## Affected diagnostic run

- scientific label: R01V2
- logical estimation slot: R01
- experiment identity: EXP-20260826-T2-26TO39-DL-18000K-R01
- run identity: RUN-20260827T171926Z-788
- final class: ABANDONED_PRETRIGGER_ZERO_SCIENTIFIC_CONTROL
- valid estimation repetition: NO
- scientific trigger consumed: NO
- applied PRB state after closeout: 26

Failure adjudication SHA256:

    595a08a77801ca13db1ea9f4037fbb8ecb249e2837497c7861c18869e679dc23

Final abandoned-run closeout SHA256:

    9e814892ffe48dd6c20bd6dd399247c13ad0bb4629426c8b977797ac4734ec58

## Original workload-start root cause

Frozen root-cause class:

    ROOT_CAUSE_CLASS=WORKLOAD_STARTUP_TOOLING_READINESS_RACE

The workload client was launched after Docker reported the receiver container
as running, but before the receiver-side iperf3 server had actually emitted:

    Server listening on 5201

The failed client timestamp preceded the timestamped server-ready marker by
approximately 3.786537 ms.

The successful historical T2 R03 acquisition had the opposite ordering:
the timestamped receiver-ready marker preceded the recorded workload start by
approximately 43.594355 ms.

Therefore:

    Docker container running != receiver application ready

This is a workload-start tooling/readiness race. It is not an O-RAN plant
failure, PRB actuation failure, or scientific response failure.

## First readiness implementation and validation finding

The first uncommitted readiness implementation had SHA256:

    a7b7d97bba978226fd248cbb7973078f8e3dcfe07b5d9436c7b50b5bbd8db53a

It introduced `wait-receiver-ready`, but its first positive self-test exposed
a second tooling race inside the readiness implementation itself.

`State.Running` and `State.Status` were read using two separate
`docker inspect` calls while the receiver was transitioning from `created`
to `running`.

One observation therefore produced the inconsistent pair:

    Running=false
    Status=running

The receiver nevertheless emitted and timestamped the exact marker:

    Server listening on 5201

That first readiness implementation was never committed and was not used for
a scientific acquisition.

## Final repair

The validated adapter SHA256 is:

    38d602c612547c4cd7fcee3110286eac0d5142da9c4b4199b5f353d1f405fad7

The final `wait-receiver-ready` gate uses one Docker state snapshot:

    RECEIVER_STATE_SNAPSHOT_MODE=SINGLE_DOCKER_INSPECT

The gate treats `created` as a transient startup state while polling, rather
than as an immediate failure.

Before an iperf3 client may be launched for a fresh scientific run, the gate
must establish all of the following:

1. the unique receiver container exists;
2. container state is read from one consistent Docker inspect snapshot;
3. startup may transition from `created` to `running` within the timeout;
4. the receiver is running when readiness is accepted;
5. the timestamped receiver capture contains the exact marker
   `Server listening on 5201`;
6. the marker is obtained before the fixed 5000 ms timeout;
7. a stale marker belonging to an already stopped receiver is rejected.

The readiness source is the timestamped receiver capture itself, not merely
Docker container state.

## Validation

The final candidate passed:

- Bash syntax validation;
- traffic-contract validation;
- positive receiver-only live self-test;
- exact timestamped readiness-marker validation;
- consistent `Running=true`, `Status=running` state at readiness acceptance;
- negative fail-closed test against the abandoned stopped R01V2 receiver;
- complete self-test cleanup.

The positive self-test did not launch an iperf3 client.

Neither readiness validation attempt issued:

- a RIC Control request;
- a scientific trigger;
- a PRB state change.

The authoritative plant state remained 26 PRB.

## Scientific contract impact

No scientific threshold, model, input step, output definition, or scientific
timing threshold is changed.

Unchanged:

- traffic direction: UDP downlink;
- offered rate: 18 Mbit/s;
- source: 10.45.1.1;
- receiver: 10.45.1.2;
- receiver interval: 0.2 s;
- planned workload duration: 3600 s;
- T2 transition: 26 -> 39 PRB;
- scientific t0: U_APPLIED_READBACK;
- pre-step minimum duration: 11 s;
- final precontrol freshness limit: 800 ms;
- executor-to-applied limit: 2800 ms;
- final-sample-to-applied limit: 3600 ms.

Only workload-start admission is strengthened.

## Replacement policy

R01V2 remains diagnostic evidence and shall never be reused.

The next logical R01 replacement requires:

- a new evidence namespace;
- a new RUN_ID;
- a new FIFO and trigger;
- the same canonical logical R01 experiment identity;
- explicit timestamped receiver-ready PASS before client launch.

The existing valid T2 estimation set still contains only R03.

Current valid estimation count:

    1 / 3

R04 remains unauthorized.
