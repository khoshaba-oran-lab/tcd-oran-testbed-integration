# Prompt 12 — SISO System Identification and PID Control

## M12-1A — Identification Experiment Design Freeze

### Status

M12-1A is the experiment-design stage preceding all new Prompt 12
identification experiments.

No PI/PID tuning, closed-loop control, or new identification experiment is
permitted until the complete M12-1A design contract has been frozen.

Current design status:

- PRB actuator semantics: FROZEN
- actuator command domain: FROZEN
- physical PRB domain: FROZEN
- identification levels: FROZEN
- primary step-transition matrix: FROZEN
- primary output sampling period: FROZEN at 0.2 s receiver-side reporting window
- pre-step admission: FROZEN at minimum 11 s plus OUTPUT_STATIONARITY_GATE
- post-step observation: FROZEN at minimum 10 s plus adaptive OUTPUT_STATIONARITY_GATE
- repetitions: FROZEN at 4 valid repetitions per directed step
- measured signals: FROZEN
- dataset schema: FROZEN with Prompt 12 SISO schema v1.0.0
- first new identification experiment: ALLOWED only after M12-1A closure checkpoint

## 1. Proven R03 actuator baseline

Prompt 11R established the runtime actuation chain

    u_cmd
      -> u_ack
      -> u_applied/readback
      -> plant response
      -> native gNB telemetry

with:

- ACTUATION_GATE=PASS;
- no gNB, UE, or 5GC restart;
- E2SM-RC enabled;
- E2SM-KPM disabled.

The successful R03 runtime used:

- srsRAN source revision:
  `9d5dd742a70e82c0813c34f57982f9507f1b6d5d`;
- R03 gNB image:
  `sha256:4af028e1849c2c23848e342681d04ec1a1d2732ee25f7d41290018c93da05eb1`;
- radio channel bandwidth: 10 MHz;
- common subcarrier spacing: 15 kHz;
- frequency range: FR1.

## 2. PRB command semantics

The SISO control input is the E2SM-RC Max PRB Policy Ratio:

    u_cmd = Max PRB Policy Ratio [%]

The implementation clamps the requested ratio to the interval:

    0 <= u_cmd <= 100

For the current 10 MHz / 15 kHz / FR1 cell configuration,

    N_cell = get_max_Nprb(10 MHz, 15 kHz, FR1) = 52 PRB

The applied absolute PRB limit is therefore

    N_cap = floor((u_cmd / 100) * 52)

for non-negative command values.

The scheduler receives the resulting absolute resource limit through
`pdsch_grant_size_limits` and `pusch_grant_size_limits`.

## 3. Frozen actuator domains

Physical command domain:

    0% <= u_cmd <= 100%

Physical cell-resource domain:

    0 PRB <= N_cap <= 52 PRB

The Prompt 12 identification domain is deliberately restricted to:

    25% <= u_cmd <= 100%

or equivalently:

    13 PRB <= N_cap <= 52 PRB

The 0% operating point is excluded from identification experiments because
system identification does not require intentional removal of essentially all
user-plane scheduling resources.

## 4. Frozen identification levels

| Level | Max PRB Policy Ratio | Applied PRB cap |
|------:|---------------------:|----------------:|
| L1 | 25% | 13 PRB |
| L2 | 50% | 26 PRB |
| L3 | 75% | 39 PRB |
| L4 | 100% | 52 PRB |

The previously observed baseline maximum DL NewTx grant of 48 PRB does not
represent the physical cell limit. It represents the largest grant actually
used under that workload. The physical cell-resource domain is 52 PRB.

## 5. Primary directed step-transition matrix

The primary identification design uses equal command increments of 25
percentage points and evaluates both increasing and decreasing transitions.

| Transition | From | To | Delta command | Delta PRB |
|-----------:|-----:|---:|--------------:|----------:|
| T1 | 25% / 13 PRB | 50% / 26 PRB | +25 pp | +13 PRB |
| T2 | 50% / 26 PRB | 75% / 39 PRB | +25 pp | +13 PRB |
| T3 | 75% / 39 PRB | 100% / 52 PRB | +25 pp | +13 PRB |
| T4 | 100% / 52 PRB | 75% / 39 PRB | -25 pp | -13 PRB |
| T5 | 75% / 39 PRB | 50% / 26 PRB | -25 pp | -13 PRB |
| T6 | 50% / 26 PRB | 25% / 13 PRB | -25 pp | -13 PRB |

The canonical primary step cycle is therefore:

    25 -> 50 -> 75 -> 100 -> 75 -> 50 -> 25 [%]

Each directed transition shall be analysed independently.

The use of both upward and downward transitions is mandatory because it allows
the experiment to detect direction-dependent dynamics, hysteresis, saturation,
and changes in local plant gain.

The 75% -> 100% transition remains part of the design even if throughput
approaches workload saturation. Such saturation is itself an important
property of the plant and shall not be removed from the identification data.

## 6. Current experimental prohibition

This paragraph records an intermediate design stage; all listed requirements are closed by later freeze sections.

Before the first new Prompt 12 experiment, the following must still be frozen:

1. sampling period;
2. pre-step steady-state duration and steady-state acceptance criterion;
3. post-step observation duration;
4. number and organization of repetitions;
5. primary and auxiliary measured signals;
6. timestamps and actuation/readback fields;
7. Prompt 12 dataset schema and experiment identifiers.

Until those items are closed:

    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 7. Frozen temporal sampling contract

### 7.1 Primary plant output

The primary SISO plant output is receiver-side downlink throughput:

    y(t) = receiver-side DL throughput

The sender-side target bitrate is not the plant output. It defines the offered
traffic load and therefore forms part of the experimental operating condition.

For identification processing, the discrete output is defined as

    y[k] = mean receiver-side DL throughput over sampling window k

with the frozen primary reporting and sampling interval

    Ts = 0.2 s

Thus, the primary identification output is a sequence of 200 ms receiver-side
throughput averages.

### 7.2 Capability evidence

The 0.2 s receiver reporting capability was verified using the exact diagnostic
toolbox image associated with the R03 user-plane measurement topology:

    image = sci-oran/toolbox:v1
    image_id = sha256:2f60d32db88bb07cfc8af06830fe5e25b3183c107591ce5044e1711eb28b0adb

The image runs:

    iperf 3.9

An isolated UDP 18 Mbit/s loopback capability test using this exact image
produced receiver-side periodic reports at:

    0.00-0.20 s
    0.20-0.40 s
    0.40-0.60 s
    ...

with:

    EXACT_TOOLBOX_RECEIVER_0P2_GATE=PASS

The capability test used Docker network mode `none` and did not attach to the
UE network namespace or generate traffic through the gNB, 5GC, or FlexRIC.

### 7.3 Multi-rate acquisition rule

Prompt 12 uses a multi-rate measurement architecture.

The following timing semantics are frozen:

| Signal | Timing rule |
|---|---|
| `u_cmd` | exact actuator-command event timestamp |
| `u_ack` | exact acknowledgement event timestamp |
| `u_applied/readback` | exact applied/readback event timestamp |
| primary receiver DL throughput `y[k]` | 0.2 s reporting windows |
| RTT | native configured cadence, currently 0.2 s where applicable |
| native gNB telemetry | preserve native timestamps and native reporting rate |
| host/container/network observability | preserve native configured sampling rate |

Raw observations shall not be assigned synthetic timestamps merely to force all
sources onto the 0.2 s grid.

Cross-source synchronization and resampling, where scientifically required,
shall be performed only in the processed-data layer and shall remain
provenance-traceable.

### 7.4 Throughput-window validity

A normal identification throughput sample shall represent one complete
0.2 s reporting window.

Partial terminal intervals, for example:

    3.00-3.04 s

shall not be treated as ordinary 0.2 s identification samples.

Startup or shutdown intervals affected by measurement-process initialization
shall be retained as raw evidence but may be excluded from model fitting when
the exclusion rule is defined deterministically and recorded in processing
provenance.

### 7.5 Current temporal-design status

The following item is now frozen:

    PRIMARY_OUTPUT_SAMPLING_PERIOD_S=0.2

The following temporal parameters are finalized by later freeze sections:

    PRE_STEP_MINIMUM_DURATION_S=11
    STEADY_STATE_ACCEPTANCE_CRITERION=FROZEN
    POST_STEP_MINIMUM_DURATION_S=10

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 8. Frozen identification workload contract

### 8.1 Traffic semantics

The identification workload shall use a fixed downlink UDP offered load:

    TRAFFIC_PROTOCOL=UDP
    TRAFFIC_DIRECTION=DOWNLINK
    TARGET_BITRATE=18M

The offered load is an experimental operating condition and is not the plant
output.

The primary plant output remains:

    y[k] = receiver-side DL throughput averaged over a 0.2 s window

### 8.2 Duration-based workload requirement

Prompt 12 shall not reproduce the R03 finite-transfer workload:

    TRANSFER_SIZE=20M

The identification workload shall instead be duration-based and continuous
across the pre-step, transition, and post-step observation intervals.

Conceptually:

    iperf3 -u -b 18M -t <experiment-duration> -i 0.2

The workload process shall already be active before an actuator transition and
shall remain active throughout the complete observation interval after that
transition.

Therefore:

    FIXED_TRANSFER_SIZE_FOR_IDENTIFICATION=PROHIBITED
    CONTINUOUS_DURATION_BASED_LOAD=REQUIRED

### 8.3 Operating-regime interpretation

Existing R03 evidence shows that the same 18 Mbit/s offered load produces
different queue regimes.

At the high-resource baseline, receiver throughput was approximately
17.8 Mbit/s with zero receiver packet loss and only a comparatively small
positive downlink queue.

At the PRB25 operating point, receiver throughput was approximately
7 Mbit/s and a multi-megabyte downlink backlog developed.

Therefore, the identification design does not require persistent backlog at
every actuator level.

The actuator range may contain both:

    actuator-limited operating regions

and:

    offered-load-limited / saturation operating regions

The 75% -> 100% transition remains intentionally included so that saturation
or loss of incremental throughput gain can be experimentally detected rather
than assumed.

### 8.4 Model-fitting consequence

A single global linear FOPDT model shall not be accepted merely because all
four actuator levels were exercised.

After acquisition, each transition shall first be classified according to its
observed local gain and operating regime.

Transitions exhibiting clear actuator-dependent output response may be used
for local linear model identification.

Transitions dominated by offered-load saturation shall be retained in the
dataset as nonlinear/saturation evidence and shall not be forced into the
linear FOPDT fit without explicit justification.

### 8.5 Queue interpretation

The native gNB downlink queue indicator `dl_bs` is an auxiliary regime and
diagnostic signal.

The following universal rules are rejected:

    dl_bs > 0  => saturated
    dl_bs = 0  => unsaturated
    delta(dl_bs) ~= 0 => steady state

Queue magnitude, trend, receiver throughput, packet loss, and actuator state
shall instead be interpreted jointly.

### 8.6 Frozen workload status

The following workload parameters are frozen:

    IDENTIFICATION_TRAFFIC_PROTOCOL=UDP
    IDENTIFICATION_TRAFFIC_DIRECTION=DOWNLINK
    IDENTIFICATION_TARGET_BITRATE=18M
    IDENTIFICATION_LOAD_MODE=DURATION_BASED_CONTINUOUS
    IDENTIFICATION_TRANSFER_SIZE_MODE=PROHIBITED

The following items are finalized by later freeze sections:

    PRE_STEP_MINIMUM_DURATION_S=11
    STEADY_STATE_ACCEPTANCE_CRITERION=FROZEN
    POST_STEP_MINIMUM_DURATION_S=10
    VALID_REPETITIONS_PER_DIRECTED_STEP=4

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 9. Frozen output-stationarity criterion

### 9.1 Definition

For Prompt 12, the term `steady state` used for pre-step admission refers
primarily to stationarity of the measured SISO output, not necessarily to a
complete equilibrium of every internal queue state.

The primary output is:

    y[k] = receiver-side DL throughput over a 0.2 s reporting window

A growing or non-zero `dl_bs` queue therefore does not automatically reject an
otherwise stationary throughput operating point.

For clarity, the formal admission condition is named:

    OUTPUT_STATIONARITY_GATE

rather than assuming full internal plant-state equilibrium.

### 9.2 Statistical window

The frozen stationarity window is:

    STATIONARITY_WINDOW_S=5
    PRIMARY_OUTPUT_TS_S=0.2
    EXPECTED_COMPLETE_SAMPLES_PER_WINDOW=25

Only complete 0.2 s receiver intervals are eligible.

Partial terminal intervals and measurement-startup fragments are excluded from
the stationarity calculation according to the previously frozen sampling
contract.

### 9.3 Throughput variability criterion

For each 5 s window, calculate:

    mean_y = mean(y[k])
    std_y  = standard deviation(y[k])
    CV_y   = 100 * std_y / mean_y

The throughput variability condition is:

    CV_y <= 5 percent

Existing R03 1 s evidence showed approximately:

    high-resource baseline:
        five-second CV = 2.08 ... 3.14 percent

    PRB25 operating point:
        five-second CV = 0.83 ... 4.34 percent

The 5 percent limit therefore provides margin above the variability already
observed in both known operating regimes.

### 9.4 Consecutive-window requirement

A single stable-looking 5 s interval is insufficient.

Pre-step admission requires two consecutive non-overlapping 5 s windows:

    W1 = 5 s
    W2 = 5 s

with:

    CV_y(W1) <= 5 percent
    CV_y(W2) <= 5 percent

and the relative difference between their means shall satisfy:

    abs(mean_y(W2) - mean_y(W1))
    -------------------------------- * 100 <= 5 percent
          mean_y(W1)

Therefore the minimum statistical observation required to establish output
stationarity is:

    OUTPUT_STATIONARITY_CONFIRMATION_S=10

### 9.5 Actuator and workload conditions

The output-stationarity gate is valid only when all of the following remain
true throughout W1 and W2:

    offered UDP load is continuously active
    actuator command is unchanged
    actuator acknowledgement/readback is valid
    applied actuator state is unchanged
    no gNB restart occurs
    no UE restart occurs
    no 5GC restart occurs

A window crossing an actuator transition is not eligible.

### 9.6 Queue and loss semantics

The gNB `dl_bs` signal is retained as an auxiliary operating-regime indicator.

It shall be used to distinguish cases such as:

    low-backlog / demand-limited regime
    persistent-backlog / actuator-limited regime
    queue build-up
    queue drain
    possible saturation or buffer-pressure regime

However, no universal condition such as:

    dl_bs == 0

or:

    delta(dl_bs) == 0

is required for OUTPUT_STATIONARITY_GATE=PASS.

Receiver packet loss is also recorded and classified but is not by itself an
automatic rejection of a stationary actuator-limited operating point.

### 9.7 Frozen criterion

The following parameters are now frozen:

    STATIONARITY_WINDOW_S=5
    OUTPUT_STATIONARITY_CV_MAX_PERCENT=5
    OUTPUT_STATIONARITY_MEAN_SHIFT_MAX_PERCENT=5
    OUTPUT_STATIONARITY_CONSECUTIVE_WINDOWS=2
    OUTPUT_STATIONARITY_CONFIRMATION_S=10

The following parameters are finalized by later freeze sections:

    PRE_STEP_MINIMUM_DURATION_S=11
    POST_STEP_MINIMUM_DURATION_S=10
    VALID_REPETITIONS_PER_DIRECTED_STEP=4

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 10. Frozen startup guard and pre-step admission

### 10.1 Startup transient evidence

Existing R03 receiver evidence shows a reproducible measurement/workload
startup transient in the first one-second interval.

For the high-resource baseline:

    first 1 s absolute deviation from subsequent mean = 7.09 percent
    second 1 s absolute deviation                   = 0.70 percent

For the PRB25 operating point:

    first 1 s absolute deviation from subsequent mean = 9.04 percent
    second 1 s absolute deviation                     = 0.61 percent

Therefore the first one second after workload measurement begins shall not be
used for pre-step output-stationarity admission.

The frozen startup guard is:

    STARTUP_GUARD_S=1

With the primary sampling interval:

    Ts=0.2 s

this corresponds nominally to:

    STARTUP_GUARD_COMPLETE_SAMPLES=5

### 10.2 Minimum pre-step duration

After the 1 s startup guard, the previously frozen
OUTPUT_STATIONARITY_GATE requires two consecutive non-overlapping
5 s windows.

Therefore:

    startup guard = 1 s
    W1            = 5 s
    W2            = 5 s

and:

    PRE_STEP_MINIMUM_DURATION_S=11

At Ts=0.2 s this corresponds nominally to:

    startup guard = 5 complete samples
    W1            = 25 complete samples
    W2            = 25 complete samples

for a minimum of:

    PRE_STEP_MINIMUM_COMPLETE_SAMPLES=55

### 10.3 Step-admission rule

The actuator transition shall not be issued merely because 11 s have elapsed.

A step is admitted only when:

    STARTUP_GUARD_COMPLETE=YES

and:

    OUTPUT_STATIONARITY_GATE=PASS

for the two immediately preceding eligible 5 s windows.

Thus:

    ELAPSED_TIME_11S != AUTOMATIC_STEP_PERMISSION

Instead:

    STEP_PERMISSION =
        elapsed_time >= 11 s
        AND OUTPUT_STATIONARITY_GATE == PASS

### 10.4 Failed initial stationarity admission

If W1 and W2 do not satisfy the frozen stationarity criterion, the actuator
command shall remain unchanged.

One additional non-overlapping 5 s output window shall be collected.

The gate shall then be reevaluated using the two most recent consecutive
eligible 5 s windows.

Conceptually:

    initial test:
        W1, W2

    if FAIL:
        collect W3
        test W2, W3

    if FAIL:
        collect W4
        test W3, W4

    ...

No actuator step may cross a failed pre-step admission window.

### 10.5 Frozen pre-step parameters

The following parameters are now frozen:

    STARTUP_GUARD_S=1
    STARTUP_GUARD_COMPLETE_SAMPLES=5
    PRE_STEP_MINIMUM_DURATION_S=11
    PRE_STEP_MINIMUM_COMPLETE_SAMPLES=55
    PRE_STEP_EXTENSION_WINDOW_S=5
    PRE_STEP_EXTENSION_COMPLETE_SAMPLES=25

The step is event-admitted by OUTPUT_STATIONARITY_GATE rather than by elapsed
time alone.

The following design parameters are finalized by later freeze sections:

    POST_STEP_MINIMUM_DURATION_S=10
    VALID_REPETITIONS_PER_DIRECTED_STEP=4

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 11. R03 step-response evidence classification

### 11.1 Recovered timeline

The R03 evidence establishes the following temporal ordering:

    before-workload end:
        2026-08-17T11:15:43Z

    PRB25 control launch:
        2026-08-17T11:19:39Z

    after-workload begin:
        2026-08-17T11:31:43Z

The measured gaps are:

    BEFORE_TO_CONTROL_GAP_S=236
    CONTROL_TO_AFTER_GAP_S=724

Therefore the baseline workload had already terminated before the PRB25
control was issued, and the post-control workload started only after the
control operation had completed.

### 11.2 Continuous-excitation classification

R03 does not contain a continuous offered-load interval spanning the actuator
transition.

Therefore:

    R03_CONTINUOUS_LOAD_ACROSS_ACTUATION=NO
    R03_TRUE_STEP_RESPONSE_DATASET=NO

The R03 experiment remains valid evidence for:

    runtime actuator functionality
    command acknowledgement
    applied/readback state
    PRB-cap enforcement
    separated before/after throughput response
    queue-regime response
    native telemetry observability

but it is not valid evidence for direct estimation of the transient response
to a PRB step under constant external excitation.

### 11.3 System-identification consequence

The following quantities shall not be estimated from the separated R03
before/after runs:

    dead time L
    time constant tau
    settling time
    rise time
    fall time
    transient overshoot

R03 steady operating points may be used as prior operating-region evidence,
but not as substitutes for Prompt 12 transition data.

In particular:

    R03_SETTLING_TIME_EVIDENCE=NOT_AVAILABLE
    R03_FOPDT_TRANSIENT_IDENTIFICATION=PROHIBITED

### 11.4 Prompt 12 requirement

Every Prompt 12 identification transition shall occur while the duration-based
18 Mbit/s UDP workload remains continuously active.

The measurement stream shall cover:

    pre-step stationary operation
    exact actuator command event
    acknowledgement/readback
    transient response
    post-step stationary operation

without stopping or restarting the offered workload at the actuator step.

The post-step observation policy therefore must be designed independently of
R03 settling-time estimates.

Current status:

    POST_STEP_MINIMUM_DURATION_S=10
    VALID_REPETITIONS_PER_DIRECTED_STEP=4
    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED

## 12. Frozen adaptive post-step observation rule

### 12.1 Transition timestamps

Every identification transition shall preserve at least:

    t_cmd
    t_ack
    t_applied_readback

The complete measurement stream shall remain active before, during, and after
these events.

The interval:

    t_cmd -> t_applied_readback

is retained as part of the end-to-end actuator-response evidence.

The corresponding actuator application latency is:

    T_actuation =
        t_applied_readback - t_cmd

### 12.2 Plant-response time origin

For plant dynamic identification, the effective step-reference timestamp is:

    PLANT_STEP_T0 = t_applied_readback

provided that the applied/readback gate is valid.

The command timestamp `t_cmd` is not discarded. It remains available for
end-to-end control-path latency analysis.

Thus Prompt 12 distinguishes:

    command-path timing

from:

    plant-response timing after confirmed actuator application

### 12.3 Throughput sample eligibility around the step

The receiver throughput process remains continuously active across the
actuator transition.

A 0.2 s throughput reporting interval that crosses `t_applied_readback` shall:

    be retained in raw evidence
    be marked as a transition-crossing interval
    not be used as an ordinary post-step stationarity sample

The first eligible post-step sample is the first complete receiver reporting
interval whose interval start is not earlier than `t_applied_readback`.

### 12.4 Minimum post-step observation

No additional measurement-startup guard is introduced after an actuator step,
because the workload and receiver measurement process remain continuously
running.

The previously frozen OUTPUT_STATIONARITY_GATE requires:

    W1 = 5 s
    W2 = 5 s

of consecutive eligible post-step samples.

Therefore:

    POST_STEP_MINIMUM_DURATION_S=10

At:

    Ts=0.2 s

this corresponds to:

    POST_STEP_MINIMUM_COMPLETE_SAMPLES=50

### 12.5 Adaptive completion rule

Ten seconds after actuator application is a minimum observation requirement,
not an automatic end of the transition experiment.

The post-step observation is complete only when the two most recent
non-overlapping eligible 5 s windows satisfy:

    CV_y(W1) <= 5 percent
    CV_y(W2) <= 5 percent

and:

    abs(mean_y(W2) - mean_y(W1))
    -------------------------------- * 100 <= 5 percent
          mean_y(W1)

Therefore:

    POST_STEP_COMPLETE =
        elapsed_since_t_applied_readback >= 10 s
        AND OUTPUT_STATIONARITY_GATE == PASS

### 12.6 Adaptive extension rule

If the first pair of post-step windows fails the stationarity gate, the
actuator command shall remain unchanged and the workload shall remain
continuously active.

One additional non-overlapping 5 s window shall be collected.

The gate shall then be reevaluated using the two most recent eligible windows:

    W1, W2

if FAIL:

    collect W3
    test W2, W3

if FAIL:

    collect W4
    test W3, W4

and so forth.

Therefore the actual post-step observation duration has the form:

    T_post_actual = 10 s + n * 5 s

where:

    n >= 0

and completion occurs only after OUTPUT_STATIONARITY_GATE=PASS.

### 12.7 Transient preservation

All valid output samples from the actuator transition through the eventual
post-step stationary regime shall remain in the raw and processed experiment
dataset.

Samples that are not part of the final stationary windows shall not be
discarded merely because they represent transient behavior.

They are required for estimation of quantities such as:

    dead time L
    time constant tau
    rise or fall dynamics
    local plant gain
    possible overshoot
    asymmetric up-step/down-step behavior

### 12.8 Queue and regime telemetry

The post-step completion decision is based on output stationarity.

However, the following auxiliary signals shall continue to be collected across
the entire post-step observation:

    dl_bs
    native gNB throughput telemetry
    packet loss
    RTT
    CPU/resource observability
    network observability

These signals classify the operating regime and possible confounders but do
not replace the primary output-stationarity gate.

### 12.9 Frozen post-step parameters

The following parameters are now frozen:

    PLANT_STEP_TIME_ORIGIN=U_APPLIED_READBACK
    POST_STEP_MINIMUM_DURATION_S=10
    POST_STEP_MINIMUM_COMPLETE_SAMPLES=50
    POST_STEP_EXTENSION_WINDOW_S=5
    POST_STEP_EXTENSION_COMPLETE_SAMPLES=25
    POST_STEP_COMPLETION_MODE=ADAPTIVE_OUTPUT_STATIONARITY

The following parameter is finalized by the later repetition freeze section:

    VALID_REPETITIONS_PER_DIRECTED_STEP=4

A finite acquisition timeout / failed-settling classification may be defined
separately as an experiment-safety bound. Such a timeout shall not be
interpreted as an assumed physical settling time.

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 13. Frozen repetition and validation contract

### 13.1 Directed-step repetition count

Each directed actuator transition shall have four valid repetitions:

    VALID_REPETITIONS_PER_DIRECTED_STEP=4

The frozen directed transitions are:

    T1: 25 -> 50 percent
    T2: 50 -> 75 percent
    T3: 75 -> 100 percent
    T4: 100 -> 75 percent
    T5: 75 -> 50 percent
    T6: 50 -> 25 percent

Therefore the minimum valid transition count is:

    DIRECTED_STEP_COUNT=6
    VALID_REPETITIONS_PER_DIRECTED_STEP=4
    TOTAL_VALID_TRANSITIONS=24

### 13.2 Estimation and validation split

For every directed step:

    R1 = estimation
    R2 = estimation
    R3 = estimation
    R4 = hold-out validation

Thus:

    ESTIMATION_REPETITIONS_PER_DIRECTED_STEP=3
    VALIDATION_REPETITIONS_PER_DIRECTED_STEP=1

The R4 hold-out transition shall not be used to estimate or tune:

    plant gain K
    dead time L
    time constant tau
    FOPDT parameters
    local linear model coefficients

R4 shall be evaluated only after the candidate model for the corresponding
operating region has been fixed using R1-R3.

### 13.3 Repetition organization

One valid repetition consists of one complete directed-step sequence:

    25 -> 50 -> 75 -> 100 -> 75 -> 50 -> 25

A complete sequence therefore contains all six directed transitions exactly
once.

Four valid complete sequences shall be acquired:

    sequence R1
    sequence R2
    sequence R3
    sequence R4

Each sequence shall have a distinct experiment/run identifier.

The workload may be restarted between complete sequences, but it shall remain
continuous across every actuator transition within a sequence.

### 13.4 Initial and intermediate admission

At the beginning of each complete sequence, the initial 25 percent operating
point shall satisfy the frozen pre-step admission contract:

    startup guard
    plus OUTPUT_STATIONARITY_GATE

For subsequent transitions within the same continuous sequence, the stationary
post-step state of the previous transition may serve as the pre-step state of
the next transition.

Therefore an additional measurement startup guard is not required between
adjacent transitions while the same measurement process and offered workload
remain continuously active.

However, every next actuator step still requires:

    OUTPUT_STATIONARITY_GATE=PASS

at the current operating point.

### 13.5 Valid-repetition gate

A transition counts toward the frozen repetition count only if all required
evidence gates are valid.

At minimum:

    workload continuity = PASS
    u_cmd timestamp = PRESENT
    u_ack = PASS
    u_applied/readback = PASS
    no gNB restart = PASS
    no UE restart = PASS
    no 5GC restart = PASS
    receiver measurement continuity = PASS
    required raw telemetry capture = PASS
    pre-step stationarity admission = PASS
    post-step observation completion = PASS

A failed or incomplete attempt shall be retained as diagnostic evidence but
shall not increment the valid repetition count.

It shall be replaced by another attempt of the same directed step within a
replacement complete sequence or an explicitly recorded replacement run.

### 13.6 Directionality rule

Upward and downward transitions shall remain separate experimental classes.

Data from:

    25 -> 50

shall not be pooled blindly with:

    50 -> 25

and similarly for the other direction pairs.

This preserves evidence for:

    asymmetric dynamics
    hysteresis
    direction-dependent dead time
    direction-dependent gain
    queue build/drain asymmetry

### 13.7 Validation isolation

The hold-out R4 dataset shall remain excluded from parameter estimation and
controller tuning until the candidate SISO model has been frozen.

After model freeze, R4 shall be used to assess predictive performance against
previously unseen transition realizations.

If R4 invalidates the model, the result shall be classified as a model
validation failure rather than silently refitting the model on R4.

Any later model revision shall create a new model version and a new validation
classification.

### 13.8 Frozen repetition parameters

The following parameters are now frozen:

    VALID_REPETITIONS_PER_DIRECTED_STEP=4
    ESTIMATION_REPETITIONS_PER_DIRECTED_STEP=3
    VALIDATION_REPETITIONS_PER_DIRECTED_STEP=1
    DIRECTED_STEP_COUNT=6
    TOTAL_VALID_TRANSITIONS=24
    REPETITION_LAYOUT=COMPLETE_SEQUENCE
    HOLDOUT_VALIDATION_REPETITION=R4

The numeric repetition-count design is therefore frozen.

M12-1A was held open until the complete design document and schema were audited for measurement, provenance, and internal consistency. That audit is now complete.

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 14. Frozen measured-signal contract

### 14.1 Measurement hierarchy

Prompt 12 separates measured information into three classes:

    CLASS_A = REQUIRED_FOR_SISO_IDENTIFICATION
    CLASS_B = REQUIRED_FOR_VALIDITY_AND_CONFOUNDER_ANALYSIS
    CLASS_C = OPTIONAL_DIAGNOSTIC

Class A defines the minimum plant input/output evidence.

Class B provides the observability required to determine whether an apparent
plant response was affected by queueing, packet loss, radio conditions,
system-resource pressure, or network-side confounders.

Class C improves diagnostic depth but its absence alone does not invalidate an
otherwise complete identification transition.

### 14.2 Class A: required for SISO identification

The following signals are mandatory for every valid directed step.

#### Actuator command

Scientific semantic:

    u_cmd = requested Max PRB Policy Ratio [%]

Required information:

    requested ratio value
    exact command-event timestamp

The physical command domain remains:

    0 <= u_cmd <= 100 percent

and the frozen identification domain remains:

    25 <= u_cmd <= 100 percent

#### Actuator acknowledgement

Required information:

    acknowledgement status
    exact acknowledgement-event timestamp

The acknowledgement shall remain distinct from applied/readback evidence.

#### Applied actuator/readback state

Required information:

    applied/readback status
    exact applied/readback-event timestamp
    applied_min_prbs
    applied_max_prbs

Existing R03 native evidence demonstrates the required source semantics with:

    PRB_ACTUATOR_APPLIED
    applied_min_prbs=0
    applied_max_prbs=13

The effective plant-response time origin remains:

    PLANT_STEP_T0 = t_applied_readback

#### Primary plant output

The primary measured output is receiver-side iperf downlink throughput.

Canonical namespace and field:

    namespace = iperf
    field     = throughput_kbit_s

Scientific definition:

    y[k] = receiver-side DL throughput over a complete 0.2 s window

Therefore:

    PRIMARY_OUTPUT_NAMESPACE=iperf
    PRIMARY_OUTPUT_FIELD=throughput_kbit_s
    PRIMARY_OUTPUT_UNIT=kbit/s
    PRIMARY_OUTPUT_TS_S=0.2

The following field shall not replace the primary output:

    netif.rx_throughput_kbit_s

because network-interface throughput is a derived rate from cumulative
interface counters and has different measurement semantics.

#### Workload condition

The configured offered load shall be recorded as an input condition.

Canonical namespace:

    traffic

Canonical configured field:

    offered_rate_kbit_s

For the frozen identification design:

    offered_rate_kbit_s = 18000

The continuous workload execution evidence shall also preserve the configured
duration and original iperf command/output.

### 14.3 Class A timestamp requirements

Every valid transition shall preserve at least:

    t_cmd
    t_ack
    t_applied_readback

and the receiver-side throughput time intervals covering:

    pre-step stationary state
    command path
    transition-crossing interval
    transient response
    post-step stationary state

Raw source timestamps shall remain unchanged.

Processed aligned representations shall use the existing project canonical
alignment coordinate:

    timestamp_utc_ns

where scientifically defensible.

No synthetic observed timestamp may be created solely from:

    k * Ts

or from an assumed nominal sampling interval.

### 14.4 Class B: iperf validity and traffic-quality observations

The following iperf fields are required alongside the primary output where
provided by the measurement tool:

    throughput_kbit_s
    loss_pct
    jitter_ms
    bytes_transferred

Canonical namespace:

    iperf

`throughput_kbit_s` is the primary plant output.

`loss_pct`, `jitter_ms`, and `bytes_transferred` are validity and
operating-regime observations.

Raw iperf output shall remain retained so that processed values are traceable
to the exact source representation.

### 14.5 Class B: native gNB telemetry

Native gNB telemetry shall be collected continuously across every directed
step at its native reporting rate.

The minimum required native gNB fields are:

    cqi
    dl_mcs
    dl_brate_kbps
    dl_nof_ok
    dl_nof_nok
    dl_error_rate
    dl_bs

Canonical namespace:

    native_gnb

These source-native field names and units shall be preserved.

In particular:

    dl_brate_kbps

is auxiliary gNB throughput telemetry and shall not replace the receiver-side
iperf primary output.

The field:

    dl_bs

is the primary queue/regime indicator but is not itself the universal
stationarity criterion.

### 14.6 Class B: RTT observations

RTT shall be retained in the canonical:

    rtt

namespace.

The observed sample field is:

    rtt_ms

Where derived latency summaries are generated, the canonical fields are:

    rtt_p50_ms
    rtt_p95_ms
    rtt_p99_ms

Percentiles are derived statistics and shall preserve their aggregation-window
and processing provenance.

### 14.7 Class B: host CPU and CPU-frequency observations

The following canonical host CPU fields shall be retained:

    cpu_utilization_pct
    cpu_core_id
    cpu_core_utilization_pct

Canonical namespace:

    host_cpu

CPU-frequency observations shall use:

    cpu_core_id
    cpu_frequency_mhz

Canonical namespace:

    cpu_freq

Host-wide and per-core CPU observations shall remain semantically distinct.

### 14.8 Class B: host load and memory observations

Canonical host-load fields:

    load_1m
    load_5m
    load_15m

Canonical namespace:

    load

Canonical memory fields:

    memory_total_bytes
    memory_used_bytes
    memory_available_bytes

Canonical namespace:

    memory

These sources retain their native configured acquisition cadence.

They shall not be artificially expanded to the 0.2 s primary-output grid at
the raw-data level.

### 14.9 Class B: network-interface observations

Canonical namespace:

    netif

Required cumulative network counters are:

    rx_bytes_total
    tx_bytes_total
    rx_packets_total
    tx_packets_total
    rx_drops_total
    tx_drops_total
    rx_errors_total
    tx_errors_total

Derived interface-rate fields may additionally include:

    rx_throughput_kbit_s
    tx_throughput_kbit_s

The cumulative counters are observations.

Throughput calculated from those counters is a derived quantity and shall
remain identified as derived.

### 14.10 Class B: container resource observations

Canonical namespace:

    container

Required container identity/resource fields where the collector supports the
corresponding runtime quantity are:

    container_id
    container_role
    container_cpu_pct
    container_memory_bytes
    container_rx_bytes_total
    container_tx_bytes_total

The scientific role represented by:

    container_role

shall remain distinct from runtime-specific container identifiers.

### 14.11 Multi-rate acquisition requirement

Prompt 12 does not require all measurement sources to produce samples at the
same rate.

The frozen acquisition architecture is multi-rate.

Primary receiver throughput:

    0.2 s reporting windows

RTT:

    native configured cadence
    currently 0.2 s where applicable

Native gNB telemetry:

    native reporting rate

Host/container/network observability:

    native configured collector rate

Actuator information:

    discrete event timestamps

Raw data shall preserve each source at its actual measurement cadence.

Any cross-source alignment, nearest-neighbor matching, aggregation,
interpolation, or resampling belongs to the processed or derived layer and
shall be explicitly provenance-traceable.

### 14.12 Class C: optional diagnostic radio fields

Additional source-native gNB fields shall be preserved when available,
including examples such as:

    ri
    pusch_snr_db
    pusch_rsrp_db
    ul_mcs
    ul_brate_kbps
    ul_nof_ok
    ul_nof_nok
    ul_error_rate
    crc_delay_ms
    bsr
    last_ta
    last_phr

These fields improve diagnosis of radio and uplink-side effects.

Their absence alone does not invalidate a transition provided the Class A and
mandatory Class B contracts are satisfied.

### 14.13 O-RAN KPM scope

O-RAN KPM measurements are not required for the Prompt 12 SISO
system-identification admission gate.

If O-RAN KPM data are available, they shall be retained under:

    oran_kpm

with their native timestamp and provenance semantics.

Absence of KPM telemetry does not invalidate Prompt 12 SISO identification.

### 14.14 Transition measurement-validity gate

A directed step counts as a valid identification transition only if the
following core conditions are satisfied:

    actuator command evidence = PASS
    actuator acknowledgement evidence = PASS
    applied/readback evidence = PASS
    receiver iperf throughput continuity = PASS
    primary 0.2 s output capture = PASS
    continuous workload evidence = PASS
    native gNB required telemetry capture = PASS
    RTT acquisition = PASS
    host/resource observability capture = PASS
    network observability capture = PASS
    no gNB restart = PASS
    no UE restart = PASS
    no 5GC restart = PASS

A failed required acquisition stream shall not be silently replaced with zero
or fabricated by interpolation.

The attempt shall remain in provenance but shall not increment the valid
repetition count.

### 14.15 Frozen measured-signal status

The measured-signal design is now frozen.

Therefore:

    MEASURED_SIGNALS_FREEZE=PASS
    PRIMARY_OUTPUT_SOURCE=IPERF_RECEIVER
    PRIMARY_OUTPUT_FIELD=throughput_kbit_s
    PRIMARY_OUTPUT_TS_S=0.2
    MULTIRATE_ACQUISITION=REQUIRED
    RAW_SOURCE_TIMESTAMP_PRESERVATION=REQUIRED
    PROCESSED_ALIGNMENT_FIELD=timestamp_utc_ns

At that intermediate stage, the final major M12-1A design item was:

    PROMPT12_DATASET_SCHEMA_FREEZE=PASS

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 15. Frozen Prompt 12 dataset architecture

### 15.1 Reuse of the existing Sci_O-RAN data model

Prompt 12 shall not create a second incompatible metadata or identity model.

The authoritative existing project contracts remain:

    datasets/schemas/sci-oran-metadata-v1.0.0.schema.json
    datasets/schemas/sci-oran-data-dictionary-v1.0.0.json
    docs/08-dataset-specification.md

The existing metadata schema remains the dataset/experiment/run/artifact/
processing-provenance envelope.

The existing data dictionary remains authoritative for already defined
canonical field names and units.

Prompt 12 adds only experiment-specific structured fields that are not already
represented by the common Sci_O-RAN vocabulary.

### 15.2 Experiment identity

Each complete valid identification sequence is one controlled scientific
experiment repeat.

The four planned repeat identities are:

    R01
    R02
    R03
    R04

The canonical experiment identifier shall use the existing project convention:

    EXP-YYYYMMDD-DL-18000K-RNN

where:

    YYYYMMDD = UTC date of the actual experiment execution
    DL       = downlink
    18000K   = frozen offered rate of 18000 kbit/s
    RNN      = R01, R02, R03, or R04

The UTC date shall not be preassigned during design freeze.

It shall be generated from the actual acquisition date.

### 15.3 Run identity and failed attempts

Every concrete execution attempt receives a canonical run identifier:

    RUN-YYYYMMDDTHHMMSSZ-NNN

A failed, aborted, rejected, or incomplete attempt shall retain:

    the same planned experiment_id when it represents the same scientific
    repeat condition

but shall receive:

    a distinct run_id

A failed run is retained in provenance and shall not be overwritten.

Only an accepted run may satisfy one of the four valid R01-R04 repetitions.

### 15.4 Dataset identity

The final dataset identifier shall use the existing convention:

    DS-YYYYMMDD-NNN-short-name

The exact dataset identifier shall be assigned only during dataset freeze.

It shall not substitute for experiment_id or run_id.

### 15.5 Raw-data architecture

Raw scientific evidence is immutable after acquisition closure.

For every run, the raw layer shall retain source evidence from at least the
following logical namespaces:

    traffic
    iperf
    actuator
    native_gnb
    rtt
    host_cpu
    cpu_freq
    load
    memory
    netif
    container
    runtime_identity
    readiness

Raw files shall preserve:

    source-native representation
    source-native timestamps where available
    acquisition-side timestamps
    exact command output
    failure evidence
    original units
    original missing values

Raw observations shall not be rewritten merely to obtain a common 0.2 s grid.

### 15.6 Receiver iperf timestamp requirement

The primary output source is receiver-side iperf throughput.

For Prompt 12, preserving only iperf relative intervals such as:

    0.00-0.20 s
    0.20-0.40 s

is insufficient for precise cross-source step-response alignment.

The acquisition wrapper shall therefore timestamp each receiver-side periodic
iperf report at collection time using:

    rx_wall_ns
    rx_mono_ns

These timestamps are observed acquisition timestamps.

The source-relative iperf fields shall also be retained:

    interval_start_s
    interval_end_s
    interval_duration_s

Thus each primary-output record preserves both:

    source-relative interval semantics

and:

    receiver-side epoch / monotonic observation timing

The existing project rule remains:

    raw timestamps are not rewritten
    timestamp normalization belongs to processed data

### 15.7 Canonical processed alignment

Processed cross-source tables shall use:

    timestamp_utc_ns

as the canonical UTC alignment coordinate.

For receiver iperf records, `timestamp_utc_ns` shall be generated
deterministically from an observed epoch-based receiver timestamp such as:

    rx_wall_ns

with the exact transformation recorded in processing provenance.

It shall not be generated solely from:

    sample_index * 0.2 s

or another assumed nominal sampling interval.

The fields:

    rx_wall_ns
    rx_mono_ns
    interval_start_s
    interval_end_s

shall remain available after normalization where scientifically useful.

### 15.8 Processed source-specific tables

Prompt 12 shall preserve multi-rate source-specific processed tables rather
than forcing all measurements into one raw or processed wide table.

The minimum logical processed tables are:

    actuator_events
    iperf_receiver
    native_gnb
    rtt
    host_cpu
    cpu_freq
    load
    memory
    netif
    container

Every processed table shall include, where applicable:

    experiment_id
    run_id
    record_id
    timestamp_utc_ns

and row/artifact provenance according to the existing dataset specification.

### 15.9 actuator_events table

The Prompt 12 actuator event table shall contain separate event records for:

    command
    acknowledgement
    applied_readback

The minimum Prompt-12-specific fields are:

    event_type
    requested_max_prb_ratio_pct
    acknowledgement_status
    applied_min_prbs
    applied_max_prbs

Field semantics:

    requested_max_prb_ratio_pct
        requested Max PRB Policy Ratio in percent

    acknowledgement_status
        acknowledgement classification

    applied_min_prbs
        applied minimum PRB limit from readback/evidence

    applied_max_prbs
        applied maximum PRB limit from readback/evidence

Fields not applicable to one event type shall be represented according to the
existing missing-value policy and shall not be replaced automatically with
zero.

### 15.10 iperf_receiver table

The minimum processed receiver table fields are:

    experiment_id
    run_id
    record_id
    timestamp_utc_ns
    rx_wall_ns
    rx_mono_ns
    interval_start_s
    interval_end_s
    interval_duration_s
    throughput_kbit_s
    loss_pct
    jitter_ms
    bytes_transferred
    interval_class

The controlled `interval_class` vocabulary shall distinguish at least:

    complete
    transition_crossing
    partial_terminal
    startup_guard

Only eligible `complete` intervals participate in ordinary stationarity
calculations.

Transition-crossing, partial-terminal, and startup-guard intervals remain
retained evidence.

### 15.11 native_gnb table

The already validated native gNB schema and its source-native naming policy
remain authoritative.

Prompt 12 shall retain at least:

    cqi
    dl_mcs
    dl_brate_kbps
    dl_nof_ok
    dl_nof_nok
    dl_error_rate
    dl_bs

together with the existing native timestamp and receive-timestamp fields.

Prompt 12 shall not redefine these fields merely for visual consistency with
another namespace.

### 15.12 Other processed observability tables

The following existing canonical vocabularies shall be reused.

RTT:

    rtt_ms

Host CPU:

    cpu_utilization_pct
    cpu_core_id
    cpu_core_utilization_pct

CPU frequency:

    cpu_core_id
    cpu_frequency_mhz

Load:

    load_1m
    load_5m
    load_15m

Memory:

    memory_total_bytes
    memory_used_bytes
    memory_available_bytes

Network interface:

    rx_bytes_total
    tx_bytes_total
    rx_packets_total
    tx_packets_total
    rx_drops_total
    tx_drops_total
    rx_errors_total
    tx_errors_total

Container:

    container_id
    container_role
    container_cpu_pct
    container_memory_bytes
    container_rx_bytes_total
    container_tx_bytes_total

Derived interface throughput may additionally use:

    rx_throughput_kbit_s
    tx_throughput_kbit_s

but these fields shall remain semantically distinct from the primary
receiver-side iperf output.

### 15.13 Derived synchronized transition dataset

Cross-source synchronization shall produce a derived analytical representation.

It shall not replace any source-specific processed table.

Each directed transition shall be identifiable by:

    experiment_id
    run_id
    transition_label

with:

    transition_label in {T1,T2,T3,T4,T5,T6}

The transition mapping remains:

    T1 = 25 -> 50
    T2 = 50 -> 75
    T3 = 75 -> 100
    T4 = 100 -> 75
    T5 = 75 -> 50
    T6 = 50 -> 25

The derived transition representation shall preserve references to the source
artifacts and processing provenance used to construct it.

### 15.14 Estimation / validation partition metadata

The experiment repeat determines the frozen model-use class:

    R01 = estimation
    R02 = estimation
    R03 = estimation
    R04 = holdout_validation

This classification shall be represented explicitly in experiment metadata or
Prompt-12-specific structured metadata.

R04 data shall not become estimation data merely by copying it into another
derived artifact.

### 15.15 Artifact contract

Every retained artifact shall follow the existing artifact metadata contract:

    artifact_id
    experiment_id
    run_id
    data_level
    namespace
    relative_path
    media_type
    byte_size
    sha256
    schema_version
    source_artifact_ids
    processing_provenance_id
    validation_status

For raw artifacts:

    source_artifact_ids is normally empty

For processed and derived artifacts:

    source_artifact_ids shall identify the direct parent evidence

and:

    processing_provenance_id

shall identify the deterministic transformation where applicable.

### 15.16 Processing provenance

Every retained processed or derived scientific artifact shall remain
traceable through the existing processing-provenance model.

At minimum it shall identify:

    processing_provenance_id
    process_name
    process_type
    created_time_utc
    input_artifact_ids
    output_artifact_ids
    software_commit
    entrypoint
    parameters

Synchronization, resampling, aggregation, model fitting, and model validation
are explicit provenance-producing transformations.

### 15.17 Data levels

Prompt 12 uses the existing three-level model:

    raw
        -> processed
            -> derived

Raw:

    immutable direct tool/acquisition evidence

Processed:

    deterministic normalization, parsing, unit conversion, and canonical
    timestamp representation

Derived:

    synchronization
    resampling
    transition segmentation
    stationarity statistics
    operating-regime classification
    model parameters
    model predictions
    validation metrics

Derived quantities shall never be presented as direct observations.

### 15.18 Prompt-12-specific machine-readable schema

A Prompt-12-specific machine-readable schema shall be created at:

    datasets/schemas/sci-oran-prompt12-siso-v1.0.0.schema.json

Its purpose is to define Prompt-12-specific structured fields that are not
already defined by the common metadata schema or common data dictionary,
including:

    experiment model-use class
    transition labels
    actuator event fields
    iperf interval classification
    Prompt 12 identification-plan constraints

It shall complement, not replace:

    sci-oran-metadata-v1.0.0.schema.json
    sci-oran-data-dictionary-v1.0.0.json

### 15.19 Current dataset-schema status

The logical Prompt 12 dataset architecture is now frozen.

Therefore:

    PROMPT12_DATASET_ARCHITECTURE_FREEZE=PASS
    EXISTING_METADATA_SCHEMA_REUSE=REQUIRED
    EXISTING_DATA_DICTIONARY_REUSE=REQUIRED
    RAW_PROCESSED_DERIVED_MODEL=REQUIRED
    SOURCE_SPECIFIC_MULTIRATE_TABLES=REQUIRED
    IPERF_RX_WALL_TIMESTAMP_CAPTURE=REQUIRED
    IPERF_RX_MONOTONIC_TIMESTAMP_CAPTURE=REQUIRED
    PROCESSED_ALIGNMENT_FIELD=timestamp_utc_ns
    ARTIFACT_PROVENANCE_GRAPH=REQUIRED

The required machine-readable Prompt 12 schema has now been created and validated:

    PROMPT12_MACHINE_READABLE_SCHEMA=CREATED_AND_VALIDATED

Therefore:

    M12_1A_INTERMEDIATE_GATE=OPEN
    NEW_IDENTIFICATION_EXPERIMENT_INTERMEDIATE_GATE=BLOCKED
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

## 16. M12-1A final design freeze

### 16.1 Closure basis

The complete Identification Experiment Design Freeze has now been audited.

The following design elements are frozen:

    actuator semantics
    actuator command domain
    physical PRB domain
    identification operating levels
    six directed step transitions
    continuous 18 Mbit/s UDP downlink workload
    receiver-side 0.2 s primary output sampling
    startup guard
    output-stationarity criterion
    pre-step admission rule
    post-step adaptive observation rule
    repetition and hold-out validation structure
    measured-signal contract
    timestamp and multi-rate alignment contract
    dataset architecture
    Prompt-12-specific machine-readable schema

### 16.2 Frozen actuator and transition design

The physical cell domain is:

    PHYSICAL_CELL_PRBS=52

The identification actuator levels are:

    25 percent  -> 13 PRB
    50 percent  -> 26 PRB
    75 percent  -> 39 PRB
    100 percent -> 52 PRB

The directed transitions are:

    T1 = 25  -> 50
    T2 = 50  -> 75
    T3 = 75  -> 100
    T4 = 100 -> 75
    T5 = 75  -> 50
    T6 = 50  -> 25

### 16.3 Frozen workload and sampling design

The identification workload is:

    protocol      = UDP
    direction     = DOWNLINK
    offered rate  = 18000 kbit/s
    load mode     = DURATION_BASED_CONTINUOUS

The primary SISO output is:

    PRIMARY_OUTPUT_SOURCE=IPERF_RECEIVER
    PRIMARY_OUTPUT_FIELD=throughput_kbit_s
    PRIMARY_OUTPUT_TS_S=0.2

The workload and receiver measurement process shall remain continuous across
every actuator transition.

### 16.4 Frozen stationarity and timing design

The frozen timing parameters are:

    STARTUP_GUARD_S=1
    STATIONARITY_WINDOW_S=5
    OUTPUT_STATIONARITY_CV_MAX_PERCENT=5
    OUTPUT_STATIONARITY_MEAN_SHIFT_MAX_PERCENT=5
    OUTPUT_STATIONARITY_CONSECUTIVE_WINDOWS=2

The minimum pre-step interval is:

    PRE_STEP_MINIMUM_DURATION_S=11

with actual actuator-step permission gated by:

    OUTPUT_STATIONARITY_GATE=PASS

The plant-response time origin is:

    PLANT_STEP_TIME_ORIGIN=U_APPLIED_READBACK

The minimum post-step interval is:

    POST_STEP_MINIMUM_DURATION_S=10

with adaptive extension:

    POST_STEP_EXTENSION_WINDOW_S=5

until:

    OUTPUT_STATIONARITY_GATE=PASS

### 16.5 Frozen repetition design

The experiment requires:

    VALID_REPETITIONS_PER_DIRECTED_STEP=4
    ESTIMATION_REPETITIONS_PER_DIRECTED_STEP=3
    VALIDATION_REPETITIONS_PER_DIRECTED_STEP=1
    TOTAL_VALID_TRANSITIONS=24

The model-use split is:

    R01 = estimation
    R02 = estimation
    R03 = estimation
    R04 = holdout_validation

R04 shall remain excluded from model fitting until the candidate model has
been frozen.

### 16.6 Frozen dataset and schema design

The existing unified Sci_O-RAN metadata and data-dictionary contracts remain
authoritative.

Prompt 12 additionally uses:

    datasets/schemas/sci-oran-prompt12-siso-v1.0.0.schema.json

The Prompt 12 schema uses JSON Schema Draft 2020-12 and has passed:

    schema syntax validation
    Draft202012Validator.check_schema
    positive instance validation
    invalid sampling-period rejection
    invalid R04 estimation-class rejection

The frozen schema SHA-256 is:

    49a84d4dc5f59954f6985dbd218bac281ca655ba13c33af36943f12091be2bd6

### 16.7 Experimental permission boundary

M12-1A authorizes the next project stage:

    open-loop SISO identification experiments

It does not authorize:

    PI tuning
    PID tuning
    closed-loop controller execution

Those activities require valid identification data and a validated plant model
from the subsequent M12-1 stages.

### 16.8 Final design-freeze status

Therefore:

    IDENTIFICATION_EXPERIMENT_DESIGN_FREEZE=PASS
    PROMPT12_DATASET_ARCHITECTURE_FREEZE=PASS
    PROMPT12_DATASET_SCHEMA_FREEZE=PASS
    PROMPT12_MACHINE_READABLE_SCHEMA=CREATED_AND_VALIDATED
    MEASURED_SIGNALS_FREEZE=PASS
    M12_1A_COMPLETE=YES

    NEW_IDENTIFICATION_EXPERIMENT=ALLOWED_OPEN_LOOP_ONLY
    PI_PID_TUNING=NOT_ALLOWED
    CLOSED_LOOP_CONTROL=NOT_ALLOWED

No new Prompt 12 identification experiment was executed during M12-1A.
