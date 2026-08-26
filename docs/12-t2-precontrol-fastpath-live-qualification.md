# Prompt 12 T2 precontrol fast-path repair and live qualification

## Status

**LIVE_QUALIFIED — repository checkpoint pending this commit.**

This record closes the precontrol freshness implementation repair required
before preparation of the Prompt-12 T2 26-to-39 PRB transition.

It does **not** constitute a T2 scientific replication and it does not
authorise the scientific 26-to-39 control trigger.

## Frozen scientific contract

The repair preserves the frozen Prompt-12 T2 contract:

- final selection: `LATEST_50_COMPLETE_CONTIGUOUS_SAMPLES`;
- two consecutive non-overlapping windows;
- 25 complete samples per window;
- 5 s per window at 0.2 s sampling;
- CV threshold: 5 percent for each window;
- mean-shift threshold: 5 percent;
- final precontrol freshness limit: 800 ms;
- scientific transition origin remains `U_APPLIED_READBACK`.

## Root cause 1: nested evaluator process

The original
`scripts/experiment-harness/prompt12-precontrol-freshness.py`
selected the correct latest 50 samples and then launched the official
stationarity evaluator in a second Python process.

The repaired implementation imports the unchanged official evaluator
in-process and reuses its own:

- root-schema loader;
- JSON Schema validator;
- interval loader;
- `evaluate()` function.

Official evaluator SHA256:

`72bf170891e597a2d001adadeb4d9a872608c45c1f4506424b757ac2d151c3dd`

Repaired precontrol SHA256:

`d12e39ee9e222aed175c26c25d60dfe785da2e23243212a548c6cd359e758a38`

Deterministic archived-fixture validation established byte-for-byte
equivalence for:

- latest-50 selected JSONL;
- official stationarity JSON;
- final precontrol JSON;
- stdout;
- stderr;
- process exit code.

Therefore:

`SEMANTIC_EQUIVALENCE_GATE=PASS`.

## Offline latency qualification

For the full archived input:

- old median: 359.475 ms;
- repaired median: 286.064 ms;
- old P95: 426.724 ms;
- repaired P95: 353.138 ms;
- improvement gate: PASS.

For the exact-50 fixture:

- old median: 320.940 ms;
- repaired median: 260.245 ms;
- old P95: 385.014 ms;
- repaired P95: 326.214 ms;
- improvement gate: PASS.

## Root cause 2: accumulated full-prefix processing

A live qualification using the complete accumulated receiver prefix
retained correct stationarity semantics but failed freshness:

- latest-sample age: 1040.005935 ms;
- maximum allowed age: 800 ms;
- snapshot-to-precontrol end: 913.726 ms;
- canonicalization alone: 516.548 ms.

The remaining bottleneck was therefore the accumulated full-prefix
parse/canonicalization path, not the stationarity mathematics.

## Bounded TAIL60 strategy

Prior Prompt-12 evidence had already established bounded TAIL60 and
exact-latest-50 fast-path behaviour.

The live qualification therefore used an edge-synchronised envelope of
the latest 60 paired raw/timestamp capture records. The official
precontrol implementation still selected exactly the latest 50 complete
contiguous canonical samples.

The envelope size is an implementation bound only; it does not change
the frozen scientific stationarity window.

## Live qualification result

PG20 produced:

- selected complete samples: 50;
- latest-sample age: **580.718284 ms**;
- maximum allowed age: **800 ms**;
- edge-to-precontrol end: **600.111 ms**;
- stationarity window binding: PASS;
- output stationarity: PASS;
- freshness: PASS;
- precontrol admission: PASS;
- precontrol process return code: 0.

Thus:

`T2_PRECONTROL_FASTPATH_LIVE_QUALIFICATION=PASS`.

## Scientific boundary

Throughout the repair and qualification:

- actuator preparation performed: NO;
- scientific control performed: NO;
- trigger write attempt count: 0;
- scientific trigger consumed: NO;
- T2 scientific trigger count: 0.

The existing T2 26-to-39 scientific trigger remains unconsumed.

## Evidence provenance

Qualification root:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-precontrol-fastpath-live-qualification-20260826T095752Z-7ba5b7a2-v1`

Closure record SHA256:

`55135532c722ad4a13808ebc43e2672524647ed5b5b43b875c1d7613c175d210`

Closure SHA256SUMS SHA256:

`3f769bf41f653f09242d385139111d3c83148898e6a21f709293ef44efe0fbda`

Primary live PASS evidence:

`/home/khoshaba/sci-oran-evidence/prompt12/t2-26to39/prompt12-t2-precontrol-fastpath-live-qualification-20260826T095752Z-7ba5b7a2-v1/live-precontrol-tail60-qualification-v1/live-precontrol.json`

SHA256:

`124f917058c60088d1d873afe3bff19b0d1d32e89985c55d0e40593b365db12a`

## Next boundary

After this repository checkpoint is confirmed on the remote branch,
the next operation is **not** the scientific 26-to-39 trigger.

The next operation is to terminate the temporary qualification workload
and verify a clean runtime boundary. Only after that may a separate,
explicitly authorised preparation operation establish the initial
26-PRB actuator state.

The scientific 26-to-39 trigger remains forbidden until preparation,
readback verification, workload/pre-step admission, and the final
freshness gate all pass.
