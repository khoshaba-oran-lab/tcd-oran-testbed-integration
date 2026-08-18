#!/usr/bin/env python3

import argparse
import json
import math
import os
import re
import statistics
import sys
from decimal import Decimal


SAMPLE_SCHEMA = "sci_oran_rtt_sample_v1"
SUMMARY_SCHEMA = "sci_oran_rtt_summary_v1"

SAMPLE_RE = re.compile(
    r"^\[(?P<epoch>[0-9]+\.[0-9]+)\].*"
    r"icmp_seq=(?P<seq>[0-9]+).*"
    r"time=(?P<rtt>[0-9.]+) ms"
)

SUMMARY_RE = re.compile(
    r"^(?P<tx>[0-9]+) packets transmitted, "
    r"(?P<rx>[0-9]+) received"
)


def nearest_rank(values, percentile):
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[max(0, rank - 1)]


def atomic_json_write(path, document):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    temporary = path + ".tmp"

    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            document,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


def write_samples(path, samples):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    temporary = path + ".tmp"

    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        for sample in samples:
            json.dump(
                sample,
                handle,
                ensure_ascii=False,
                sort_keys=True,
            )
            handle.write("\n")

        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


def parse_ping(path):
    samples = []
    ping_tx = None
    ping_rx = None

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            sample_match = SAMPLE_RE.search(line)

            if sample_match:
                epoch_text = sample_match.group("epoch")
                seq = int(sample_match.group("seq"))
                rtt_ms = float(sample_match.group("rtt"))

                epoch_ns = int(
                    Decimal(epoch_text) * Decimal(1_000_000_000)
                )

                samples.append(
                    {
                        "schema": SAMPLE_SCHEMA,
                        "timestamp_source":
                            "iputils_ping_D_reply_side_software_epoch",
                        "timestamp_utc_ns": epoch_ns,
                        "icmp_seq": seq,
                        "rtt_ms": rtt_ms,
                    }
                )

                continue

            summary_match = SUMMARY_RE.search(line)

            if summary_match:
                ping_tx = int(summary_match.group("tx"))
                ping_rx = int(summary_match.group("rx"))

    if not samples:
        raise ValueError("no valid RTT samples found")

    return samples, ping_tx, ping_rx


def build_summary(samples, ping_tx, ping_rx):
    rtts = [sample["rtt_ms"] for sample in samples]
    sequences = sorted(
        set(sample["icmp_seq"] for sample in samples)
    )

    seq_min = sequences[0]
    seq_max = sequences[-1]

    closed_expected = seq_max - seq_min + 1
    unique_replies = len(sequences)
    internal_missing = closed_expected - unique_replies

    if internal_missing < 0:
        raise ValueError("invalid sequence accounting")

    closed_loss_percent = (
        100.0 * internal_missing / closed_expected
    )

    if len(rtts) > 1:
        masd_ms = sum(
            abs(rtts[index] - rtts[index - 1])
            for index in range(1, len(rtts))
        ) / (len(rtts) - 1)

        stddev_ms = statistics.pstdev(rtts)
    else:
        masd_ms = 0.0
        stddev_ms = 0.0

    terminal_unresolved = None

    if ping_tx is not None:
        terminal_unresolved = max(
            0,
            ping_tx - seq_max,
        )

    return {
        "schema": SUMMARY_SCHEMA,
        "measurement": {
            "metric": "icmp_round_trip_time",
            "canonical_loss_method":
                "closed_sequence_internal_missing",
            "terminal_boundary_policy":
                "right_censored_unresolved_probe_not_network_loss",
            "timestamp_source":
                "iputils_ping_D_reply_side_software_epoch",
        },
        "samples": {
            "count": len(rtts),
            "seq_min": seq_min,
            "seq_max": seq_max,
            "unique_replies": unique_replies,
            "closed_interval_expected": closed_expected,
            "internal_missing_replies": internal_missing,
            "closed_interval_loss_percent":
                closed_loss_percent,
        },
        "rtt_ms": {
            "min": min(rtts),
            "mean": statistics.mean(rtts),
            "stddev_population": stddev_ms,
            "p50_nearest_rank":
                nearest_rank(rtts, 0.50),
            "p95_nearest_rank":
                nearest_rank(rtts, 0.95),
            "p99_nearest_rank":
                nearest_rank(rtts, 0.99),
            "max": max(rtts),
            "mean_absolute_successive_difference":
                masd_ms,
        },
        "raw_ping_termination": {
            "packets_transmitted": ping_tx,
            "packets_received": ping_rx,
            "terminal_unresolved_probes":
                terminal_unresolved,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert Sci_O-RAN raw iputils ping RTT evidence "
            "into processed samples and derived QoS statistics."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Raw ping log produced by the RTT adapter.",
    )

    parser.add_argument(
        "--samples-output",
        required=True,
        help="Processed RTT JSONL output path.",
    )

    parser.add_argument(
        "--summary-output",
        required=True,
        help="Derived RTT QoS summary JSON output path.",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print("RTT_INPUT_NOT_FOUND", file=sys.stderr)
        return 66

    try:
        samples, ping_tx, ping_rx = parse_ping(args.input)
        summary = build_summary(samples, ping_tx, ping_rx)

        write_samples(
            args.samples_output,
            samples,
        )

        atomic_json_write(
            args.summary_output,
            summary,
        )

    except (OSError, ValueError) as exc:
        print(
            f"RTT_PROCESSING_ERROR={exc}",
            file=sys.stderr,
        )
        return 65

    print(f"RTT_SAMPLE_COUNT={len(samples)}")
    print(
        "RTT_INTERNAL_MISSING_REPLIES="
        f"{summary['samples']['internal_missing_replies']}"
    )
    print(
        "RTT_CLOSED_INTERVAL_LOSS_PERCENT="
        f"{summary['samples']['closed_interval_loss_percent']:.6f}"
    )
    print(
        "RTT_P50_MS="
        f"{summary['rtt_ms']['p50_nearest_rank']:.3f}"
    )
    print(
        "RTT_P95_MS="
        f"{summary['rtt_ms']['p95_nearest_rank']:.3f}"
    )
    print(
        "RTT_P99_MS="
        f"{summary['rtt_ms']['p99_nearest_rank']:.3f}"
    )
    print(
        "RTT_MASD_MS="
        f"{summary['rtt_ms']['mean_absolute_successive_difference']:.3f}"
    )
    print("RTT_PROCESSOR=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
