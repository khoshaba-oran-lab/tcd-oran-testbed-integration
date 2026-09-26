#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys


RATIO_ENV_KEY = "SCI_ORAN_MAX_PRB_RATIO"
ALLOWED_RATIOS = {25, 50, 75, 100}
TRIGGER_TOKEN = "TRIGGER\n"

BINDING_SCHEMA = "sci_oran_prompt12_v2_pretrigger_ratio_binding_v1"
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

REQUIRED_BINDING_KEYS = {
    "schema",
    "binding_id",
    "experiment_id",
    "run_id",
    "transition_label",
    "transition_index",
    "requested_ratio_pct",
    "created_utc",
}


class ReaderContractError(Exception):
    pass


def validate_identity(value, name):
    if not isinstance(value, str) or not IDENTITY_PATTERN.fullmatch(value):
        raise ReaderContractError(f"{name}_INVALID")
    return value


def parse_actuator_argv(raw):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReaderContractError("ACTUATOR_ARGV_JSON_INVALID") from exc

    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ReaderContractError("ACTUATOR_ARGV_INVALID")

    return value


def parse_ratio_binding_paths(raw):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReaderContractError(
            "RATIO_BINDING_PATHS_JSON_INVALID"
        ) from exc

    if not isinstance(value, list) or len(value) != 6:
        raise ReaderContractError(
            "RATIO_BINDING_PATH_COUNT_INVALID"
        )

    paths = []

    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item:
            raise ReaderContractError(
                "RATIO_BINDING_PATH_INVALID"
            )

        path = pathlib.Path(item)

        if not path.is_absolute():
            raise ReaderContractError(
                "RATIO_BINDING_PATH_NOT_ABSOLUTE"
            )

        expected_name = f"T{index}.binding.json"

        if path.name != expected_name:
            raise ReaderContractError(
                "RATIO_BINDING_PATH_ORDER_INVALID:"
                f"{path.name}:{expected_name}"
            )

        paths.append(path)

    if len(set(paths)) != 6:
        raise ReaderContractError(
            "RATIO_BINDING_PATH_DUPLICATE"
        )

    return paths


def validate_existing_fifo(value):
    path = pathlib.Path(value)

    try:
        info = path.stat()
    except OSError as exc:
        raise ReaderContractError(
            f"FIFO_STAT_FAILED:{path}:{exc}"
        ) from exc

    if not stat.S_ISFIFO(info.st_mode):
        raise ReaderContractError(
            f"FIFO_PATH_NOT_FIFO:{path}"
        )

    return path


def parse_created_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReaderContractError(
            "BINDING_CREATED_UTC_INVALID"
        )

    try:
        parsed = datetime.datetime.fromisoformat(
            value[:-1] + "+00:00"
        )
    except ValueError as exc:
        raise ReaderContractError(
            "BINDING_CREATED_UTC_INVALID"
        ) from exc

    if parsed.tzinfo is None:
        raise ReaderContractError(
            "BINDING_CREATED_UTC_INVALID"
        )

    return parsed.astimezone(datetime.timezone.utc)


def consumed_path_for(path):
    return path.with_name(path.name + ".consumed.json")


def load_and_validate_binding(
    path,
    *,
    expected_experiment_id,
    expected_run_id,
    expected_transition_index,
    reader_started_utc,
    consumed_binding_ids,
):
    consumed_path = consumed_path_for(path)

    if consumed_path.exists():
        raise ReaderContractError(
            f"BINDING_ALREADY_CONSUMED:{path}"
        )

    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ReaderContractError(
            f"BINDING_MISSING:{path}"
        ) from exc
    except OSError as exc:
        raise ReaderContractError(
            f"BINDING_STAT_FAILED:{path}:{exc}"
        ) from exc

    if stat.S_ISLNK(info.st_mode):
        raise ReaderContractError(
            f"BINDING_SYMLINK_PROHIBITED:{path}"
        )

    if not stat.S_ISREG(info.st_mode):
        raise ReaderContractError(
            f"BINDING_NOT_REGULAR_FILE:{path}"
        )

    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    try:
        binding = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReaderContractError(
            f"BINDING_JSON_INVALID:{path}"
        ) from exc

    if not isinstance(binding, dict):
        raise ReaderContractError(
            "BINDING_OBJECT_INVALID"
        )

    if set(binding) != REQUIRED_BINDING_KEYS:
        raise ReaderContractError(
            "BINDING_KEYS_INVALID"
        )

    if binding["schema"] != BINDING_SCHEMA:
        raise ReaderContractError(
            "BINDING_SCHEMA_INVALID"
        )

    binding_id = binding["binding_id"]

    if not isinstance(binding_id, str) or not binding_id:
        raise ReaderContractError(
            "BINDING_ID_INVALID"
        )

    if binding_id in consumed_binding_ids:
        raise ReaderContractError(
            f"BINDING_ID_REUSED:{binding_id}"
        )

    if binding["experiment_id"] != expected_experiment_id:
        raise ReaderContractError(
            "BINDING_EXPERIMENT_ID_MISMATCH"
        )

    if binding["run_id"] != expected_run_id:
        raise ReaderContractError(
            "BINDING_RUN_ID_MISMATCH"
        )

    expected_label = f"T{expected_transition_index}"

    if binding["transition_label"] != expected_label:
        raise ReaderContractError(
            "BINDING_TRANSITION_LABEL_MISMATCH"
        )

    if binding["transition_index"] != expected_transition_index:
        raise ReaderContractError(
            "BINDING_TRANSITION_INDEX_MISMATCH"
        )

    ratio = binding["requested_ratio_pct"]

    if (
        not isinstance(ratio, int)
        or isinstance(ratio, bool)
        or ratio not in ALLOWED_RATIOS
    ):
        raise ReaderContractError(
            f"BINDING_RATIO_INVALID:{ratio}"
        )

    created_utc = parse_created_utc(
        binding["created_utc"]
    )

    now_utc = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0)

    if created_utc < reader_started_utc:
        raise ReaderContractError(
            "BINDING_STALE"
        )

    if created_utc > now_utc + datetime.timedelta(seconds=5):
        raise ReaderContractError(
            "BINDING_CREATED_IN_FUTURE"
        )

    return binding, digest


def fsync_directory(path):
    fd = os.open(str(path), os.O_RDONLY)

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def consume_binding_once(path):
    consumed_path = consumed_path_for(path)

    if consumed_path.exists():
        raise ReaderContractError(
            f"BINDING_ALREADY_CONSUMED:{path}"
        )

    try:
        os.link(path, consumed_path)
    except FileExistsError as exc:
        raise ReaderContractError(
            f"BINDING_ALREADY_CONSUMED:{path}"
        ) from exc
    except OSError as exc:
        raise ReaderContractError(
            f"BINDING_CONSUME_LINK_FAILED:{path}:{exc}"
        ) from exc

    try:
        fsync_directory(path.parent)

        os.unlink(path)

        fsync_directory(path.parent)

    except Exception as exc:
        raise ReaderContractError(
            f"BINDING_CONSUME_UNCERTAIN:{path}:{exc}"
        ) from exc

    return consumed_path


def execute_actuator_once(
    actuator_argv,
    actuator_env,
):
    completed = subprocess.run(
        list(actuator_argv),
        env=actuator_env,
        shell=False,
        check=False,
    )

    if completed.returncode != 0:
        raise ReaderContractError(
            "actuator execution failed with "
            f"returncode={completed.returncode}; replay prohibited"
        )


def run_reader(
    fifo_path,
    actuator_argv,
    ratio_binding_paths,
    experiment_id,
    run_id,
):
    experiment_id = validate_identity(
        experiment_id,
        "EXPERIMENT_ID",
    )
    run_id = validate_identity(
        run_id,
        "RUN_ID",
    )

    fifo_path = validate_existing_fifo(fifo_path)

    reader_started_utc = datetime.datetime.now(
        datetime.timezone.utc
    ).replace(microsecond=0)

    consumed_binding_ids = set()
    next_transition_index = 1

    print(
        "PROMPT12_V2_READER_PREARMED=YES "
        f"experiment_id={experiment_id} "
        f"run_id={run_id} "
        "ratio_binding_count=6",
        flush=True,
    )

    try:
        fifo_fd = os.open(
            str(fifo_path),
            os.O_RDONLY,
        )
    except OSError as exc:
        raise ReaderContractError(
            f"cannot open FIFO for reading: {fifo_path}: {exc}"
        ) from exc

    with os.fdopen(
        fifo_fd,
        mode="r",
        encoding="utf-8",
        errors="strict",
        newline="",
    ) as fifo:
        while True:
            token = fifo.readline()

            if token == "":
                raise ReaderContractError(
                    "FIFO reached EOF; automatic reader restart prohibited"
                )

            if token != TRIGGER_TOKEN:
                print(
                    "PROMPT12_V2_READER_TOKEN_REJECTED="
                    + json.dumps(token),
                    file=sys.stderr,
                    flush=True,
                )
                continue

            if next_transition_index > 6:
                raise ReaderContractError(
                    "NO_REMAINING_RATIO_BINDING"
                )

            binding_path = ratio_binding_paths[
                next_transition_index - 1
            ]

            binding, binding_sha256 = (
                load_and_validate_binding(
                    binding_path,
                    expected_experiment_id=experiment_id,
                    expected_run_id=run_id,
                    expected_transition_index=next_transition_index,
                    reader_started_utc=reader_started_utc,
                    consumed_binding_ids=consumed_binding_ids,
                )
            )

            consumed_path = consume_binding_once(
                binding_path
            )

            binding_id = binding["binding_id"]
            ratio = binding["requested_ratio_pct"]

            consumed_binding_ids.add(binding_id)

            print(
                "PROMPT12_V2_READER_BINDING_CONSUMED=YES "
                f"binding_id={binding_id} "
                f"transition={binding['transition_label']} "
                f"ratio_pct={ratio} "
                f"binding_sha256={binding_sha256} "
                f"consumed_path={consumed_path}",
                flush=True,
            )

            actuator_env = os.environ.copy()
            actuator_env[RATIO_ENV_KEY] = str(ratio)

            print(
                "PROMPT12_V2_READER_TRIGGER_ACCEPTED=YES "
                f"transition={binding['transition_label']}",
                flush=True,
            )

            execute_actuator_once(
                actuator_argv=actuator_argv,
                actuator_env=actuator_env,
            )

            print(
                "PROMPT12_V2_READER_ACTUATOR_EXECUTION_COMPLETED=YES "
                f"transition={binding['transition_label']} "
                f"ratio_pct={ratio}",
                flush=True,
            )

            next_transition_index += 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Prompt-12 production persistent local FIFO reader. "
            "The FIFO must already exist. Each accepted TRIGGER "
            "requires one valid, unconsumed transition-specific "
            "ratio binding."
        )
    )

    parser.add_argument(
        "--fifo-path",
        required=True,
    )
    parser.add_argument(
        "--actuator-argv-json",
        required=True,
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
        "--ratio-binding-paths-json",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    actuator_argv = parse_actuator_argv(
        args.actuator_argv_json
    )

    ratio_binding_paths = parse_ratio_binding_paths(
        args.ratio_binding_paths_json
    )

    return run_reader(
        fifo_path=args.fifo_path,
        actuator_argv=actuator_argv,
        ratio_binding_paths=ratio_binding_paths,
        experiment_id=args.experiment_id,
        run_id=args.run_id,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReaderContractError as exc:
        print(
            f"PROMPT12_V2_READER_GATE=FAIL ERROR={exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(2)
