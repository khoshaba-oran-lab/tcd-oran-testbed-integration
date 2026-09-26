#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import uuid


SCHEMA = "sci_oran_prompt12_v2_pretrigger_ratio_binding_v1"
ALLOWED_RATIOS = {25, 50, 75, 100}
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class BindingError(Exception):
    pass


def nonempty_identity(value, name):
    if not isinstance(value, str) or not IDENTITY_PATTERN.fullmatch(value):
        raise BindingError(f"{name}_INVALID")
    return value


def validate_transition(label, index):
    if not isinstance(index, int) or not 1 <= index <= 6:
        raise BindingError("TRANSITION_INDEX_INVALID")

    expected = f"T{index}"
    if label != expected:
        raise BindingError(
            f"TRANSITION_LABEL_INDEX_MISMATCH:{label}:{index}"
        )

    return label, index


def validate_ratio(value):
    if value not in ALLOWED_RATIOS:
        raise BindingError(f"REQUESTED_RATIO_INVALID:{value}")
    return value


def validate_output_path(value):
    path = pathlib.Path(value)

    if not path.is_absolute():
        raise BindingError("OUTPUT_PATH_NOT_ABSOLUTE")

    if not path.parent.is_dir():
        raise BindingError("OUTPUT_PARENT_NOT_DIRECTORY")

    return path


def utc_now():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def make_binding_id(
    experiment_id,
    run_id,
    transition_label,
    transition_index,
):
    return (
        f"{experiment_id}:"
        f"{run_id}:"
        f"{transition_label}:"
        f"{transition_index}:"
        f"{uuid.uuid4().hex}"
    )


def encode_binding(binding):
    return (
        json.dumps(
            binding,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def write_exclusive(path, payload):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL

    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise BindingError("OUTPUT_ALREADY_EXISTS") from exc
    except OSError as exc:
        raise BindingError(f"OUTPUT_CREATE_FAILED:{exc}") from exc

    created = True

    try:
        total = 0

        while total < len(payload):
            written = os.write(fd, payload[total:])
            if written <= 0:
                raise BindingError("OUTPUT_SHORT_WRITE")
            total += written

        os.fsync(fd)

    except Exception:
        try:
            os.close(fd)
        finally:
            if created:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
        raise

    else:
        os.close(fd)

    path.chmod(0o600)


def build_binding(
    experiment_id,
    run_id,
    transition_label,
    transition_index,
    requested_ratio_pct,
):
    experiment_id = nonempty_identity(
        experiment_id,
        "EXPERIMENT_ID",
    )
    run_id = nonempty_identity(
        run_id,
        "RUN_ID",
    )

    transition_label, transition_index = validate_transition(
        transition_label,
        transition_index,
    )

    requested_ratio_pct = validate_ratio(
        requested_ratio_pct
    )

    return {
        "schema": SCHEMA,
        "binding_id": make_binding_id(
            experiment_id,
            run_id,
            transition_label,
            transition_index,
        ),
        "experiment_id": experiment_id,
        "run_id": run_id,
        "transition_label": transition_label,
        "transition_index": transition_index,
        "requested_ratio_pct": requested_ratio_pct,
        "created_utc": utc_now(),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Materialize exactly one Prompt-12 V2 "
            "transition-specific pre-trigger ratio binding."
        )
    )

    parser.add_argument(
        "--experiment-id",
        required=True,
    )
    parser.add_argument(
        "--run-id",
        required=True,
    )
    parser.add_argument(
        "--transition-label",
        required=True,
    )
    parser.add_argument(
        "--transition-index",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--requested-ratio-pct",
        required=True,
        type=int,
    )
    parser.add_argument(
        "--output",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    output = validate_output_path(args.output)

    binding = build_binding(
        experiment_id=args.experiment_id,
        run_id=args.run_id,
        transition_label=args.transition_label,
        transition_index=args.transition_index,
        requested_ratio_pct=args.requested_ratio_pct,
    )

    payload = encode_binding(binding)
    digest = hashlib.sha256(payload).hexdigest()

    write_exclusive(output, payload)

    actual = hashlib.sha256(output.read_bytes()).hexdigest()
    if actual != digest:
        raise BindingError("OUTPUT_SHA256_VERIFICATION_FAILED")

    print(f"BINDING_ID={binding['binding_id']}")
    print(f"BINDING_PATH={output}")
    print(f"BINDING_SHA256={digest}")
    print(
        "REQUESTED_RATIO_PCT="
        f"{binding['requested_ratio_pct']}"
    )
    print(
        "TRANSITION="
        f"{binding['transition_label']}"
    )
    print("RATIO_BOUND=PASS")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BindingError as exc:
        print(
            f"RATIO_BOUND=FAIL ERROR={exc}",
            file=sys.stderr,
        )
        raise SystemExit(2)
