#!/usr/bin/env python3

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tarfile


AUTHORITATIVE_LOG_PATH = "/tmp/gnb.log"
AUTHORITATIVE_SOURCE = "CONTAINER:/tmp/gnb.log"
DOCKER_LOGS_IS_AUTHORITATIVE = False

MARKER = "PRB_ACTUATOR_APPLIED"

MARKER_RE = re.compile(
    r"(?P<timestamp>"
    r"\d{4}-\d{2}-\d{2}[T ]"
    r"\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r")"
    r".*?\bPRB_ACTUATOR_APPLIED\b"
    r".*?\bapplied_min_prbs=(?P<minimum>\d+)\b"
    r".*?\bapplied_max_prbs=(?P<maximum>\d+)\b"
)


def parse_time(value):
    parsed = dt.datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if parsed.tzinfo is not None:
        parsed = (
            parsed
            .astimezone(dt.timezone.utc)
            .replace(tzinfo=None)
        )

    return parsed


def parse_markers(text):
    result = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if MARKER not in line:
            continue

        match = MARKER_RE.search(line)

        if not match:
            result.append(
                {
                    "line_number": line_number,
                    "timestamp": None,
                    "applied_min_prbs": None,
                    "applied_max_prbs": None,
                    "raw": line,
                    "parse_status": "UNPARSED",
                }
            )
            continue

        result.append(
            {
                "line_number": line_number,
                "timestamp": parse_time(
                    match.group("timestamp")
                ),
                "applied_min_prbs": int(
                    match.group("minimum")
                ),
                "applied_max_prbs": int(
                    match.group("maximum")
                ),
                "raw": line,
                "parse_status": "PASS",
            }
        )

    return result


def evaluate_markers(
    markers,
    window_start,
    window_end,
    expected_min,
    expected_max,
):
    in_window = [
        item
        for item in markers
        if (
            item["timestamp"] is not None
            and window_start
            <= item["timestamp"]
            <= window_end
        )
    ]

    expected = [
        item
        for item in in_window
        if (
            item["applied_min_prbs"]
            == expected_min
            and item["applied_max_prbs"]
            == expected_max
        )
    ]

    if len(expected) == 1:
        gate = "PASS"
        selected = expected[0]
    elif len(expected) == 0:
        gate = "FAIL_NOT_FOUND"
        selected = None
    else:
        gate = "FAIL_AMBIGUOUS"
        selected = None

    return {
        "window_marker_count": len(in_window),
        "expected_marker_count": len(expected),
        "gate": gate,
        "selected": selected,
    }


def inspect_container(container):
    command = [
        "docker",
        "inspect",
        "-f",
        "{{.State.Running}}"
        "|{{.State.StartedAt}}"
        "|{{.Image}}",
        container,
    ]

    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "docker inspect failed: "
            + proc.stderr.strip()
        )

    fields = proc.stdout.strip().split("|", 2)

    if len(fields) != 3:
        raise RuntimeError(
            "unexpected docker inspect output"
        )

    return {
        "running": fields[0],
        "started_at": fields[1],
        "image_id": fields[2],
    }


def copy_authoritative_log(container):
    command = [
        "docker",
        "cp",
        "-L",
        container + ":" + AUTHORITATIVE_LOG_PATH,
        "-",
    ]

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if proc.stdout is None or proc.stderr is None:
        raise RuntimeError(
            "failed to open docker cp streams"
        )

    payload = None
    member_name = None

    try:
        archive = tarfile.open(
            fileobj=proc.stdout,
            mode="r|*",
        )

        for member in archive:
            if not member.isfile():
                continue

            handle = archive.extractfile(member)

            if handle is None:
                continue

            payload = handle.read()
            member_name = member.name
            break

    finally:
        proc.stdout.close()

    stderr = proc.stderr.read()
    proc.stderr.close()

    rc = proc.wait()

    if rc != 0:
        raise RuntimeError(
            "docker cp failed rc="
            + str(rc)
            + ": "
            + stderr.decode(
                "utf-8",
                errors="replace",
            ).strip()
        )

    if payload is None:
        raise RuntimeError(
            "docker cp archive contained no regular file"
        )

    return member_name, payload


def serialise_marker(item):
    if item is None:
        return None

    result = dict(item)

    timestamp = result.get("timestamp")

    if timestamp is not None:
        result["timestamp"] = timestamp.isoformat()

    return result


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--container",
        required=True,
    )

    parser.add_argument(
        "--operation-id",
        required=True,
    )

    parser.add_argument(
        "--expected-image-id",
        required=True,
    )

    parser.add_argument(
        "--expected-started-at",
        required=True,
    )

    parser.add_argument(
        "--window-start",
        required=True,
    )

    parser.add_argument(
        "--window-end",
        required=True,
    )

    parser.add_argument(
        "--expected-min-prbs",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--expected-max-prbs",
        type=int,
        required=True,
    )

    args = parser.parse_args()

    window_start = parse_time(
        args.window_start
    )

    window_end = parse_time(
        args.window_end
    )

    if window_end < window_start:
        raise SystemExit(
            "window-end precedes window-start"
        )

    identity = inspect_container(
        args.container
    )

    if identity["running"] != "true":
        raise SystemExit(
            "container is not running"
        )

    if (
        identity["image_id"]
        != args.expected_image_id
    ):
        raise SystemExit(
            "container image identity mismatch"
        )

    if (
        identity["started_at"]
        != args.expected_started_at
    ):
        raise SystemExit(
            "container incarnation mismatch"
        )

    member_name, payload = copy_authoritative_log(
        args.container
    )

    text = payload.decode(
        "utf-8",
        errors="replace",
    )

    markers = parse_markers(text)

    result = evaluate_markers(
        markers=markers,
        window_start=window_start,
        window_end=window_end,
        expected_min=args.expected_min_prbs,
        expected_max=args.expected_max_prbs,
    )

    output = {
        "schema":
            "sci_oran_prompt12_authoritative_prb_readback_v1",
        "operation_id":
            args.operation_id,
        "authoritative_source":
            AUTHORITATIVE_SOURCE,
        "docker_logs_is_authoritative":
            DOCKER_LOGS_IS_AUTHORITATIVE,
        "container":
            args.container,
        "container_started_at":
            identity["started_at"],
        "container_image_id":
            identity["image_id"],
        "log_archive_member":
            member_name,
        "log_size_bytes":
            len(payload),
        "log_sha256":
            hashlib.sha256(payload).hexdigest(),
        "marker_count_total":
            len(markers),
        "window_start":
            window_start.isoformat(),
        "window_end":
            window_end.isoformat(),
        "expected_min_prbs":
            args.expected_min_prbs,
        "expected_max_prbs":
            args.expected_max_prbs,
        "window_marker_count":
            result["window_marker_count"],
        "expected_marker_count":
            result["expected_marker_count"],
        "selected":
            serialise_marker(
                result["selected"]
            ),
        "u_applied_readback_gate":
            result["gate"],
    }

    print(
        json.dumps(
            output,
            sort_keys=True,
        )
    )

    if result["gate"] != "PASS":
        return 20

    return 0


if __name__ == "__main__":
    sys.exit(main())
