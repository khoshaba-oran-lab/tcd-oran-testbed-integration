# Sci_O-RAN Prompt12 — SISO-first Experimental Research Roadmap (v1.0)

**Status:** PROPOSED — scientific planning document; not an authorisation to run experiments or modify lifecycle state.  
**Prepared:** 2026-10-09  
**Repository destination:** `docs/12-siso-experimental-research-roadmap-v1.md`  
**Programme:** Tb3 virtual E2E RAN / Prompt12 system identification  
**Scientific priority:** trustworthy SISO measurements first; multivariable modelling deferred.

## 1. Purpose and decisions

This roadmap records three research decisions:

1. **Reduce the time to defensible experimental evidence.** Acquisition of a single target condition (e.g., a valid 39-PRB observation under an 18 Mbit/s offered load) must not require repeated infrastructure debugging over successive sessions. Move preventable configuration failures into a bounded, offline pre-start qualification phase.
2. **Finish the essential SISO research before expanding scope.** First acquire and independently validate the prescribed PRB transitions, identify and validate the SISO dynamics, and establish limits of applicability. Do not make a multivariable/MIMO model a prerequisite for these results.
3. **Extend the scientific analysis in a separate programme.** Once the fixed-load SISO series is closed, measure goodput versus offered load at multiple PRB limits and investigate saturation and resource productivity without retroactively changing the frozen Prompt12 series.

This document supplements, but does **not** amend, the frozen experiment design, contracts, lifecycle procedures, evidence requirements, or existing transition authorisations. If this roadmap conflicts with a frozen scientific or operational contract, the latter prevails pending an explicitly reviewed change.

## 2. Scientific model and terminology

The existing Prompt12 experiment is a **single-input, single-output (SISO) system-identification study**, not a claim about the number of physical radio antennas.

- **Input** `u(t)`: authoritative applied PRB limit, derived from `U_APPLIED_READBACK` (`applied_max_prbs`), not merely a requested quota.
- **Output** `y(t)`: downlink UDP receiver application-layer goodput, stored in the canonical `throughput_kbit_s` measurement field.
- **Fixed reference offered load**: 18 Mbit/s UDP downlink for the frozen T1–T6 sequence.
- **KPM**: not required by the frozen Prompt12 contract.
- **Primary question**: how does received goodput respond to a controlled change in the applied PRB limit under a reproducible load and software environment?

Use **goodput** for the useful receiver-side application payload rate. Reserve **UDP datagram loss ratio** for a secondary diagnostic metric computed from datagram counters; a difference between configured offered load and measured receiver goodput is **not**, by itself, proof of the exact packet-loss percentage.

## 3. Baseline status (historical checkpoint, not a live-state assertion)

As of the 2026-10-08 sprint closeout:

| Item | Recorded position | Scientific interpretation |
| --- | --- | --- |
| T1: 13 → 26 PRB | Historical R04 CLOSED / VALIDATED (2026-08-22) | Validated historical transition; preserve original evidence and provenance. |
| T1 receiver goodput | Approximately 7.2852 → 9.6148 Mbit/s | Absolute response +2.3296 Mbit/s; relative response ≈ +32.0%. |
| T2: 26 → 39 PRB | NOT_EXECUTED in the 2026-10-08 attempts | No validated 39-PRB plant response from those attempts. |
| T2 R01–R04 | Receiver baseline observations at 26 PRB | Useful supporting data; not substitutes for the missing controlled transition. |
| T2 R04 precontrol | Stationarity PASS; retrospective freshness PASS | Historical admission evidence does not retroactively turn the failed live attempt into a validated T2. |
| T2 R05 | BLOCKED: `EXPERIMENT_ID_INVALID` during materialisation | No PRB control; archival allocation retained. |
| Tb3 lifecycle | 2026-10-08 canonical day-stop PASS | Stop operation ID was consumed; never replay it. |

The 2026-10-08 published Git checkpoint was `2a49c164d9c9c8d407a2869074faec04ce520545`. **Recheck the current repository HEAD before any subsequent repository change**, because later work (including pre-start protection) may have advanced it. Do not pin new procedures to this historical SHA.

## 4. Workstream A — acquisition quality and time-to-evidence

### A1. Offline qualification before day-start

Use the canonical, repository-tracked **Pre-Start Guard** and existing materialisers to validate the selected unique experiment/run identity and the preparation contracts *before* activating the Tb3 lifecycle. This is a gate, not an additional scientific experiment.

Required checks, implemented through existing canonical tools where available:

- expected controller/runtime hosts, repository identity, branch and clean worktree;
- valid and unused `experiment_id`, `run_id`, operation IDs and evidence destinations;
- no pre-existing conflicting runtime root, FIFO, provider or run directory;
- frozen configuration, JSON schemas, file provenance, hashes and expected dependencies;
- correct ordering: the runtime-profile materialiser owns initial RUN directory creation; provider launch owns provider runtime root/FIFO creation;
- production bindings, resume materialisation and T2-specific transition contract;
- no unexpected already-running Tb3 components when an offline check requires a stopped testbed.

A **successful offline check must not** launch containers, run scientific traffic, trigger the FIFO, issue an actuator request, change PRB, replay lifecycle operations or alter existing scientific evidence. Any temporary qualification data must be separate from canonical evidence and handled according to the installed guard's verified cleanup contract.

**Admission result:** `PRESTART_GATE=PASS` or `PRESTART_GATE=BLOCKED` with a precise error code and affected contract. A BLOCKED result forbids proceeding to day-start for that candidate without an explicit new decision.

### A2. Short and deterministic live sprint

The live phase is for acquisition, not infrastructure development:

1. A separately authorised canonical **day-start** on `coll.vntu.org`.
2. A bounded runtime-readiness check: expected components, user plane, initial applied PRB readback and evidence writer readiness; do not repeat already qualified static checks without cause.
3. One explicitly authorised T2 scientific acquisition, with exactly-once PRB control when all precontrol gates pass.
4. Independent evidence adjudication and a separately authorised canonical **day-stop**.

At a substantial structural failure: **STOP → preserve evidence → classify → day-stop → repair offline → regress/qualify → fresh authorisation**. No automatic replay of traffic, FIFO events, PRB requests, consumed operation IDs or lifecycle actions.

Operational wrappers shall keep the login shell available and distinguish `PASS`, `FAIL`, `BLOCKED` and `NOT_EXECUTED`. Require exact host declaration and one approved operational action per turn; do not make a single action silently invoke unrelated mutations.

### A3. Quantify whether reliability improvements pay off

Record per session, without changing frozen scientific thresholds:

| Process indicator | Definition | Intended use |
| --- | --- | --- |
| **Time to first valid evidence** | From completed day-start to first independently accepted scientific run | Primary end-to-end productivity indicator. |
| **Pre-start rejection count** | Candidate configurations rejected before day-start | Measure prevention rather than live disruption. |
| **Live structural failure count** | Failures from software/contract plumbing after day-start | Must trend downward across comparable sessions. |
| **Validated transitions per authorised session** | Number of transitions independently CLOSED / VALIDATED | Scientific throughput, not merely playbook PASS. |
| **Evidence completeness** | Proportion of runs with all mandatory files, hashes, timestamps, readback and receiver samples | Reproducibility. |
| **Manual diagnostic actions per validated transition** | Number of manual corrective inspections during live work | Detect recurring diagnostic loops. |

Establish a baseline from available logs, then set realistic improvement targets after observing the new pre-start workflow. **Do not invent an hour-based service-level target or relax scientific tests solely to improve these numbers.**

## 5. Workstream B — complete and validate the fixed-load SISO series

### B1. Frozen transitions and ordering

| Transition | Applied PRB limit |
| --- | --- |
| T1 | 13 → 26 — historical validated baseline |
| T2 | 26 → 39 — immediate priority |
| T3 | 39 → 52 |
| T4 | 52 → 39 |
| T5 | 39 → 26 |
| T6 | 26 → 13 |

Complete T2 before approving T3–T6. A later T1 replication may be useful after the full sequence because the software platform has evolved; treat it as a **separate run with new identifiers** and never overwrite or replay the historical validated T1.

### B2. Preserve the acquisition contract

- DL UDP offered load: 18 Mbit/s; duration: 180 s; measurement interval: 0.2 s.
- The frozen pre-observation, stationarity, freshness, post-observation and timing requirements remain authoritative. The recent acquisition implementation uses two 5-second/25-sample precontrol windows with CV ≤ 5%, between-window mean shift ≤ 5% and freshness age ≤ 800 ms; verify against the exact tracked contract at execution time rather than replacing it with prose here.
- Record each `U_CMD`, `U_ACK`, `U_APPLIED_READBACK` and the receiver-side response; a command or acknowledgement is not proof that PRBs were applied.
- Exclude samples outside the authorised transition window when computing pre/post summaries.
- Preserve raw data, timestamps, experiment/run/operation IDs, script and image identities, hashes and the independent validator's report.

**T2 closure rule:** classify T2 as `CLOSED / VALIDATED` only when an explicitly authorised exactly-once 26 → 39 PRB command, authoritative 39-PRB readback, contemporaneous receiver response, required stationarity and provenance checks, and independent evidence validation all pass. Otherwise keep `BLOCKED`, `FAIL` or `NOT_EXECUTED` as appropriate.

### B3. Minimal SISO model deliverables

1. Canonical time-aligned `u(t)`/`y(t)` transition dataset, with quality flags and immutable provenance.
2. Baseline descriptive characteristics: pre/post goodput, dispersion, transient response and observed stationarity.
3. A **simple, explainable reference model** (e.g., a low-order ARX model) with documented delay/order selection and residual diagnostics.
4. A challenger model only if warranted by data and measurable improvement (e.g., transfer-function or state-space form); avoid unconstrained model proliferation.
5. Independent holdout validation, preferably separating runs/sessions rather than only randomly mixing nearby time samples.
6. Report uncertainty, fit statistics, residual autocorrelation, operating-point dependence and conditions under which identification is inconclusive.

The scientific claim must match the data's actual excitation and coverage. Do not claim generalisation beyond the tested PRB range or the 18 Mbit/s operating load on the strength of the fixed-load sequence alone.

## 6. Workstream C — offered-load characterisation (separate, subsequent study)

**Rationale:** 18 Mbit/s is a controlled offered-load reference, useful for identifying the PRB response near constrained throughput. It is not an evidence-backed universal optimum. A reviewer is entitled to ask whether the observed SISO dynamics and PRB productivity hold under other loads.

### C1. Candidate static load matrix

After B is validated, propose a separate, versioned protocol with candidate PRB limits **13, 26, 39 and 52** and offered UDP loads **6, 10, 14, 18 and 22 Mbit/s** (20 candidate operating points). These values are **design candidates**, not authorised new experimental settings; in particular, verify source, receiver and platform feasibility before admitting 22 Mbit/s.

At each admitted operating point:

- apply and verify the intended PRB limit using authoritative readback;
- hold offered load constant during a measurement segment;
- capture measured sender rate, receiver goodput, variability, time window, environment and diagnostic UDP counters;
- run independent validation using a separately approved static-test protocol;
- use multiple runs (e.g., three) where feasible, distribute across sessions, and manage order effects without violating lifecycle or exact-once control.

Do not retroactively alter T1–T6 or combine these new samples into the frozen dataset without explicit provenance and a scientific requalification decision.

### C2. Primary analysis metrics

Let `G(D,N)` be receiver application-layer goodput, `D` the **measured or explicitly identified configured** offered rate, and `N` the **authoritatively applied PRB cap**.

| Metric | Definition | Interpretation / caveat |
| --- | --- | --- |
| Receiver goodput | `G` (Mbit/s) | Primary scientific output. |
| Normalised delivered rate | `G / D` | Use **measured sender rate** for delivery normalisation; if `D` is only the configured target, label it *target-load attainment ratio*. |
| PRB-cap-normalised goodput | `G / N` (Mbit/s per capped PRB) | Productivity relative to the **configured cap**; not actual PRB utilisation or spectral efficiency. |
| Incremental goodput gain | `(G2 - G1) / (N2 - N1)` | PRB-response slope over a stated pair of operating points and fixed offered load. |
| Relative goodput gain | `(G2 - G1) / G1` | State baseline explicitly. |
| UDP datagram loss ratio | Lost datagrams / sent datagrams, using matched instrument counters | **Diagnostic only**; do not estimate exact loss by subtracting receiver rate from configured load. |

Investigate the onset of saturation, the shape of `G(D,N)`, repeatability, potential scheduler/CPU bottlenecks and how the incremental PRB gain varies with the offered load. The illustrative approximation `G(D,N) ≈ min(D, C(N))` is a **hypothesis/visual aid**, not an empirically established law or fitted model.

### C3. Optional dynamic offered-load series

Only after the static characterisation is adequate, consider load steps (for example, 6 → 10 → 14 → 18 Mbit/s) at **fixed** PRB cap. This tests transient demand response and queue effects and requires its own control/evidence contract. If PRB cap and offered load later become **two simultaneously varying, independently controlled inputs**, that would be a distinct multivariable identification programme, not a requirement for closing SISO.

## 7. Scope boundary — defer multivariable/MIMO identification

Do **not** initiate a two-input/two-output (or other multivariable) identification campaign until all of the following hold:

- the fixed-load SISO T1–T6 evidence is independently validated;
- a defensible reference SISO model, uncertainty and residual/holdout diagnostics exist;
- static offered-load sensitivity and saturation characteristics have been measured in a separately approved protocol;
- an explicit new research question demonstrates why the additional model input/output is needed;
- the extra observables and independent actuators are available and identifiable.

In this roadmap, **MIMO model** means *multi-input, multi-output system identification*; it must not be confused with radio-antenna MIMO. This deferral is a deliberate scope decision, not a negative judgement on either research direction.

## 8. Publication and review evidence

A future paper should answer, with traceable evidence:

1. Why was the fixed 18 Mbit/s offered load chosen, and which claims apply **only** at that load?
2. Were applied PRB limits verified by independent readback rather than inferred from control requests?
3. How does the useful **receiver goodput** increase as PRB caps change, and with what uncertainty?
4. What evidence rules out or documents confounding sender, user-plane, CPU, queue and timing bottlenecks?
5. Where does saturation begin as a function of offered load and PRB cap?
6. Is the reported PRB-normalised indicator based on **allocated cap** or actual measured PRB use?
7. Can another researcher reconstruct every plotted point from raw evidence, manifests and validation results?
8. Which results belong to validated Prompt12 identification, and which are exploratory or follow-up static-load observations?

Proposed visual outputs: transition time traces; pre/post distributions and uncertainty intervals; goodput–PRB curves at fixed load; goodput–offered-load curves at fixed PRB; the static `G(D,N)` response surface with clearly marked tested region; per-transition incremental goodput gains. Produce charts with transparent source-data provenance and distinguish measured points from illustrative/interpolated results.

## 9. Milestones and acceptance criteria

| Milestone | Completion evidence | Must not be misrepresented as |
| --- | --- | --- |
| M0: offline readiness | Versioned, qualified pre-start guard and a new candidate with `PRESTART_GATE=PASS` | Authorisation for day-start or traffic. |
| M1: T2 scientific closure | Complete readback/plant/receiver evidence and independent `CLOSED / VALIDATED` | Merely obtaining 26-PRB baseline traffic. |
| M2: T3–T6 closure | Each transition independently qualified; no replayed identities | One general success flag for the entire sequence. |
| M3: SISO model | Reproducible dataset, identified model, independent validation, limitations | Universal model over all loads. |
| M4: load-dependence map | Separately authorised static-test protocol, repeated points, independent validation | A modification of frozen Prompt12. |
| M5: publishable interpretation | Uncertainty, bottleneck checks, transparent figures and claim boundaries | Unsupported causality or universal resource efficiency. |

**Priority ordering:** M0 → M1 → M2 → M3 → M4 → M5. A later MIMO/multivariable decision is outside the critical path.

## 10. Operational ownership and change control

- **Controller:** `coll.vntu.org`; **runtime:** `tb3-dell`.
- Continue to use canonical lifecycle wrappers and Ansible orchestration.
- Require explicit approval before consequential repository/runtime mutations, day-start/day-stop, traffic, FIFO trigger or PRB actuation; use a fresh operation identity each time.
- Keep repairs auditable: classify each defect `FIXED` with tracked repair and regression evidence, or `DEFERRED` with documented risk and return condition; a workaround alone is not a permanent fix.
- This planning document is **not** a source of authority for experimental thresholds, operation IDs, target identities, timing or container state. The actual frozen manifest, committed contracts and independently checked raw evidence remain authoritative.

### Next immediate action after this roadmap is reviewed

Publish **this document only** as a reviewed documentation change in the authoritative repository. Then, in a separately authorised operating session, verify the installed pre-start guard against the current repository HEAD and select a fresh, contract-valid T2 EXP/RUN identity before canonical day-start. Do not run a scientific experiment as part of publishing the plan.
