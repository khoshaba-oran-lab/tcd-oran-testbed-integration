#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time


SCHEMA = "sci_oran_iperf_receiver_line_capture_v1"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run a receiver-side command, preserve its stdout byte-for-byte, "
            "and record observed wall/monotonic receive timestamps for each "
            "stdout line."
        )
    )
    parser.add_argument("--raw-output", required=True)
    parser.add_argument("--timestamp-output", required=True)
    parser.add_argument("--stderr-output", required=True)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute; normally specified after --",
    )

    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    if not args.command:
        parser.error("receiver command is required after --")

    return args


def ensure_parent(path):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def main():
    args = parse_args()

    for path in (
        args.raw_output,
        args.timestamp_output,
        args.stderr_output,
    ):
        ensure_parent(path)

    child = None

    def forward_signal(signum, _frame):
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGINT, forward_signal)
    signal.signal(signal.SIGTERM, forward_signal)

    raw_offset = 0
    sequence = 0

    with open(args.raw_output, "xb", buffering=0) as raw_handle, \
         open(
             args.timestamp_output,
             "x",
             encoding="utf-8",
             newline="\n",
             buffering=1,
         ) as timestamp_handle, \
         open(args.stderr_output, "xb", buffering=0) as stderr_handle:

        child = subprocess.Popen(
            args.command,
            stdout=subprocess.PIPE,
            stderr=stderr_handle,
            bufsize=0,
        )

        if child.stdout is None:
            raise RuntimeError("receiver stdout pipe was not created")

        while True:
            line = child.stdout.readline()

            if line == b"":
                break

            # These are acquisition timestamps observed when the complete
            # stdout line becomes available to this wrapper.
            rx_wall_ns = time.time_ns()
            rx_mono_ns = time.monotonic_ns()

            offset_start = raw_offset
            raw_handle.write(line)
            # Make each complete receiver line visible to concurrent
            # read-only consumers such as the online stationarity gate.
            # This does not alter the byte-exact raw evidence.
            raw_handle.flush()
            raw_offset += len(line)

            record = {
                "schema": SCHEMA,
                "sequence": sequence,
                "rx_wall_ns": rx_wall_ns,
                "rx_mono_ns": rx_mono_ns,
                "raw_offset_start": offset_start,
                "raw_offset_end": raw_offset,
                "raw_line_length_bytes": len(line),
                "raw_line_sha256": hashlib.sha256(line).hexdigest(),
                "line_utf8": line.decode("utf-8", errors="replace").rstrip(
                    "\r\n"
                ),
            }

            timestamp_handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
            timestamp_handle.flush()

            sequence += 1

        return child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
