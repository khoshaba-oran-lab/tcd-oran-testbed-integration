#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP


SCHEMA = "sci_oran_iperf_receiver_interval_parse_v1"
PRIMARY_TS_S = Decimal("0.2")
DURATION_TOLERANCE_S = Decimal("0.000001")


INTERVAL_RE = re.compile(
    r"""
    ^\[\s*(?P<stream_id>\d+)\]\s+
    (?P<start>\d+(?:\.\d+)?)-(?P<end>\d+(?:\.\d+)?)\s+
    sec\s+
    (?P<transfer_value>\d+(?:\.\d+)?)\s+
    (?P<transfer_unit>Bytes|KBytes|MBytes|GBytes)\s+
    (?P<bitrate_value>\d+(?:\.\d+)?)\s+
    (?P<bitrate_unit>bits/sec|Kbits/sec|Mbits/sec|Gbits/sec)
    (?:
        \s+
        (?P<jitter_ms>\d+(?:\.\d+)?)\s+ms\s+
        (?P<lost_datagrams>\d+)/
        (?P<total_datagrams>\d+)\s+
        \((?P<loss_pct>\d+(?:\.\d+)?)%\)
    )?
    (?:\s+(?P<role>sender|receiver))?
    \s*$
    """,
    re.VERBOSE,
)


TRANSFER_MULTIPLIER = {
    "Bytes": Decimal(1),
    "KBytes": Decimal(1024),
    "MBytes": Decimal(1024) ** 2,
    "GBytes": Decimal(1024) ** 3,
}


BITRATE_TO_KBIT = {
    "bits/sec": Decimal("0.001"),
    "Kbits/sec": Decimal("1"),
    "Mbits/sec": Decimal("1000"),
    "Gbits/sec": Decimal("1000000"),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Verify timestamped receiver raw-line evidence and parse "
            "iperf3 interval records without rewriting acquisition timestamps."
        )
    )
    parser.add_argument("--raw-input", required=True)
    parser.add_argument("--timestamp-input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def decimal_to_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite numeric value")
    return result


def parse_interval(line):
    match = INTERVAL_RE.match(line)

    if match is None:
        return None

    start = Decimal(match.group("start"))
    end = Decimal(match.group("end"))

    if end <= start:
        return None

    duration = end - start

    # Long aggregate sender/receiver summary records are not periodic samples.
    if duration > PRIMARY_TS_S + DURATION_TOLERANCE_S:
        return None

    if abs(duration - PRIMARY_TS_S) <= DURATION_TOLERANCE_S:
        interval_shape = "complete_0p2"
        normalized_duration = PRIMARY_TS_S
    elif Decimal(0) < duration < PRIMARY_TS_S:
        interval_shape = "partial_terminal_candidate"
        normalized_duration = duration
    else:
        return None

    transfer_value = Decimal(match.group("transfer_value"))
    transfer_unit = match.group("transfer_unit")

    bitrate_value = Decimal(match.group("bitrate_value"))
    bitrate_unit = match.group("bitrate_unit")

    transferred_bytes = int(
        (
            transfer_value * TRANSFER_MULTIPLIER[transfer_unit]
        ).to_integral_value(rounding=ROUND_HALF_UP)
    )

    throughput_kbit_s = (
        bitrate_value * BITRATE_TO_KBIT[bitrate_unit]
    )

    jitter_text = match.group("jitter_ms")
    loss_text = match.group("loss_pct")
    lost_text = match.group("lost_datagrams")
    total_text = match.group("total_datagrams")

    return {
        "stream_id": int(match.group("stream_id")),
        "interval_start_s": decimal_to_float(start),
        "interval_end_s": decimal_to_float(end),
        "interval_duration_s": decimal_to_float(normalized_duration),
        "throughput_kbit_s": decimal_to_float(throughput_kbit_s),
        "jitter_ms": (
            decimal_to_float(Decimal(jitter_text))
            if jitter_text is not None
            else None
        ),
        "loss_pct": (
            decimal_to_float(Decimal(loss_text))
            if loss_text is not None
            else None
        ),
        "bytes_transferred": transferred_bytes,
        "lost_datagrams": (
            int(lost_text) if lost_text is not None else None
        ),
        "total_datagrams": (
            int(total_text) if total_text is not None else None
        ),
        "iperf_role": match.group("role"),
        "interval_shape": interval_shape,
        "source_transfer_value": str(transfer_value),
        "source_transfer_unit": transfer_unit,
        "source_bitrate_value": str(bitrate_value),
        "source_bitrate_unit": bitrate_unit,
    }


def main():
    args = parse_args()

    with open(args.raw_input, "rb") as raw_handle:
        raw_bytes = raw_handle.read()

    with open(args.timestamp_input, encoding="utf-8") as handle:
        timestamp_rows = [
            json.loads(line)
            for line in handle
            if line.strip()
        ]

    parsed_rows = []

    previous_sequence = None
    raw_offset_base = None
    previous_wall_ns = None
    previous_mono_ns = None

    for timestamp_row in timestamp_rows:
        assert (
            timestamp_row["schema"]
            == "sci_oran_iperf_receiver_line_capture_v1"
        )

        sequence = timestamp_row["sequence"]

        if previous_sequence is not None:
            assert sequence == previous_sequence + 1

        start_offset = timestamp_row["raw_offset_start"]
        end_offset = timestamp_row["raw_offset_end"]

        if raw_offset_base is None:
            raw_offset_base = start_offset

        local_start_offset = start_offset - raw_offset_base
        local_end_offset = end_offset - raw_offset_base

        assert (
            0
            <= local_start_offset
            < local_end_offset
            <= len(raw_bytes)
        )

        raw_line = raw_bytes[
            local_start_offset:local_end_offset
        ]

        assert len(raw_line) == timestamp_row["raw_line_length_bytes"]

        assert (
            hashlib.sha256(raw_line).hexdigest()
            == timestamp_row["raw_line_sha256"]
        )

        decoded_line = raw_line.decode(
            "utf-8",
            errors="replace",
        ).rstrip("\r\n")

        assert decoded_line == timestamp_row["line_utf8"]

        wall_ns = timestamp_row["rx_wall_ns"]
        mono_ns = timestamp_row["rx_mono_ns"]

        assert isinstance(wall_ns, int) and wall_ns > 0
        assert isinstance(mono_ns, int) and mono_ns > 0

        if previous_wall_ns is not None:
            assert wall_ns >= previous_wall_ns
            assert mono_ns > previous_mono_ns

        interval = parse_interval(decoded_line)

        if interval is not None:
            record = {
                "schema": SCHEMA,
                "source_sequence": sequence,
                "rx_wall_ns": wall_ns,
                "rx_mono_ns": mono_ns,
                "source_raw_offset_start": start_offset,
                "source_raw_offset_end": end_offset,
                "source_raw_line_sha256": (
                    timestamp_row["raw_line_sha256"]
                ),
            }

            record.update(interval)
            parsed_rows.append(record)

        previous_sequence = sequence
        previous_wall_ns = wall_ns
        previous_mono_ns = mono_ns

    with open(
        args.output,
        "x",
        encoding="utf-8",
        newline="\n",
    ) as output_handle:
        for record in parsed_rows:
            output_handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

    print(f"TIMESTAMP_SOURCE_RECORDS={len(timestamp_rows)}")
    print(f"PARSED_INTERVAL_RECORDS={len(parsed_rows)}")
    print("RAW_INTEGRITY_VERIFICATION=PASS")
    print("IPERF_INTERVAL_PARSE=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
