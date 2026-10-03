#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import signal
import stat
import subprocess
import sys
import time


SCHEMA = (
    "sci_oran_prompt12_v2_production_"
    "provider_manager_launcher_v1"
)

ALLOCATION_SCHEMA = (
    "sci_oran_r6_prompt12_r01_prelaunch_allocation_v1"
)

AUTHORIZATION_TOKEN = (
    "AUTHORISE_PROMPT12_PROVIDER_ADMISSION"
)

FIFO_TOKEN = "@PROMPT12_ACTUATOR_FIFO@"


class LauncherError(Exception):
    def __init__(self, reason, rc=65):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


def utc_now():
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise LauncherError(label + "_INVALID")

    if parsed <= 0:
        raise LauncherError(label + "_INVALID")

    return parsed


def absolute_file(value, label):
    path = pathlib.Path(value)

    if not path.is_absolute():
        raise LauncherError(label + "_NOT_ABSOLUTE")

    if not path.is_file():
        raise LauncherError(label + "_NOT_FILE")

    return path


def new_absolute_file(value, label):
    path = pathlib.Path(value)

    if not path.is_absolute():
        raise LauncherError(label + "_NOT_ABSOLUTE")

    if os.path.lexists(str(path)):
        raise LauncherError(label + "_ALREADY_EXISTS")

    if not path.parent.is_dir():
        raise LauncherError(label + "_PARENT_NOT_DIRECTORY")

    return path


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def read_json(path, label):
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise LauncherError(
            label + "_JSON_INVALID"
        ) from exc

    return value


def write_json_exclusive(path, value):
    try:
        with path.open(
            "x",
            encoding="utf-8",
        ) as handle:
            json.dump(
                value,
                handle,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
    except FileExistsError as exc:
        raise LauncherError(
            "LAUNCHER_RECORD_ALREADY_EXISTS"
        ) from exc

    path.chmod(0o600)


def read_process_start_identity(pid):
    try:
        boot_id = pathlib.Path(
            "/proc/sys/kernel/random/boot_id"
        ).read_text(
            encoding="utf-8"
        ).strip()

        raw = pathlib.Path(
            f"/proc/{pid}/stat"
        ).read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise LauncherError(
            "PROCESS_START_IDENTITY_UNAVAILABLE"
        ) from exc

    right_parenthesis = raw.rfind(")")

    if right_parenthesis < 0:
        raise LauncherError(
            "PROCESS_STAT_SHAPE_INVALID"
        )

    tail = raw[
        right_parenthesis + 2:
    ].split()

    if len(tail) < 20:
        raise LauncherError(
            "PROCESS_STAT_SHAPE_INVALID"
        )

    start_ticks = tail[19]

    return (
        f"{boot_id}:{pid}:{start_ticks}"
    )


def terminate_manager(process):
    if process is None:
        return

    if process.poll() is not None:
        return

    try:
        os.killpg(
            process.pid,
            signal.SIGTERM,
        )
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(
            process.pid,
            signal.SIGKILL,
        )
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def validate_allocation(path):
    value = read_json(
        path,
        "ALLOCATION",
    )

    if not isinstance(value, dict):
        raise LauncherError(
            "ALLOCATION_NOT_OBJECT"
        )

    if value.get("schema") != ALLOCATION_SCHEMA:
        raise LauncherError(
            "ALLOCATION_SCHEMA_INVALID"
        )

    required_strings = (
        "experiment_id",
        "run_id",
        "runtime_root",
        "fifo_path",
        "provider_identity",
    )

    for key in required_strings:
        item = value.get(key)

        if (
            not isinstance(item, str)
            or not item
        ):
            raise LauncherError(
                "ALLOCATION_"
                + key.upper()
                + "_INVALID"
            )

    required_true = (
        "r01_identity_allocated",
    )

    required_false = (
        "runtime_root_created",
        "fifo_created",
        "provider_started",
        "reader_started",
        "runtime_profile_materialized",
        "ratio_bindings_materialized",
        "trigger_executed",
        "control_executed",
        "traffic_executed",
    )

    for key in required_true:
        if value.get(key) is not True:
            raise LauncherError(
                "ALLOCATION_"
                + key.upper()
                + "_NOT_TRUE"
            )

    for key in required_false:
        if value.get(key) is not False:
            raise LauncherError(
                "ALLOCATION_"
                + key.upper()
                + "_NOT_FALSE"
            )

    runtime_root = pathlib.Path(
        value["runtime_root"]
    )

    fifo_path = pathlib.Path(
        value["fifo_path"]
    )

    if not runtime_root.is_absolute():
        raise LauncherError(
            "RUNTIME_ROOT_NOT_ABSOLUTE"
        )

    if not fifo_path.is_absolute():
        raise LauncherError(
            "FIFO_PATH_NOT_ABSOLUTE"
        )

    if fifo_path.parent != runtime_root:
        raise LauncherError(
            "FIFO_PATH_PARENT_MISMATCH"
        )

    if fifo_path.name != "actuator.fifo":
        raise LauncherError(
            "FIFO_PATH_NAME_INVALID"
        )

    if os.path.lexists(
        str(runtime_root)
    ):
        raise LauncherError(
            "RUNTIME_ROOT_ALREADY_EXISTS"
        )

    if os.path.lexists(
        str(fifo_path)
    ):
        raise LauncherError(
            "FIFO_PATH_ALREADY_EXISTS"
        )

    return value


def validate_frozen_config(path):
    value = read_json(
        path,
        "FROZEN_CONFIG",
    )

    if not isinstance(value, dict):
        raise LauncherError(
            "FROZEN_CONFIG_NOT_OBJECT"
        )

    timeout_ms = positive_int(
        value.get(
            "timeline_readiness_timeout_ms"
        ),
        "READINESS_TIMEOUT_MS",
    )

    poll_ms = positive_int(
        value.get(
            "timeline_readiness_poll_ms"
        ),
        "READINESS_POLL_MS",
    )

    if poll_ms > timeout_ms:
        raise LauncherError(
            "READINESS_POLL_EXCEEDS_TIMEOUT"
        )

    return timeout_ms, poll_ms


def validate_provider_launch(path):
    value = read_json(
        path,
        "PROVIDER_LAUNCH",
    )

    if (
        not isinstance(value, list)
        or not value
    ):
        raise LauncherError(
            "PROVIDER_LAUNCH_ARGV_INVALID"
        )

    if not all(
        isinstance(item, str)
        and item
        for item in value
    ):
        raise LauncherError(
            "PROVIDER_LAUNCH_ARGV_INVALID"
        )

    if value.count(FIFO_TOKEN) != 1:
        raise LauncherError(
            "FIFO_TOKEN_OCCURRENCE_COUNT_INVALID"
        )

    return value


def validate_admission(
    path,
    allocation,
):
    value = read_json(
        path,
        "PROVIDER_ADMISSION",
    )

    exact = {
        "state": "ADMITTED",
        "runtime_root":
            allocation["runtime_root"],
        "fifo_path":
            allocation["fifo_path"],
        "provider_identity":
            allocation["provider_identity"],
        "provider_restart_count": 0,
        "reader_readiness_gate": "PASS",
        "readiness_method":
            "O_WRONLY_NONBLOCK_ZERO_BYTE_OPEN",
        "readiness_writer_fd_held": True,
        "trigger_write_attempt_count": 0,
        "trigger_write_success_count": 0,
        "control_executed": False,
        "traffic_executed": False,
    }

    for key, expected in exact.items():
        if value.get(key) != expected:
            raise LauncherError(
                "PROVIDER_ADMISSION_"
                + key.upper()
                + "_MISMATCH"
            )

    provider_pid = value.get(
        "provider_pid"
    )

    if (
        not isinstance(provider_pid, int)
        or provider_pid <= 0
    ):
        raise LauncherError(
            "PROVIDER_PID_INVALID"
        )

    recorded_identity = value.get(
        "provider_process_start_identity"
    )

    if (
        not isinstance(
            recorded_identity,
            str,
        )
        or not recorded_identity
    ):
        raise LauncherError(
            "PROVIDER_PROCESS_START_IDENTITY_INVALID"
        )

    observed_identity = (
        read_process_start_identity(
            provider_pid
        )
    )

    if (
        observed_identity
        != recorded_identity
    ):
        raise LauncherError(
            "PROVIDER_PROCESS_START_IDENTITY_MISMATCH"
        )

    runtime_root = pathlib.Path(
        allocation["runtime_root"]
    )

    fifo_path = pathlib.Path(
        allocation["fifo_path"]
    )

    if not runtime_root.is_dir():
        raise LauncherError(
            "RUNTIME_ROOT_NOT_DIRECTORY_AFTER_ADMISSION"
        )

    try:
        fifo_stat = fifo_path.stat()
    except OSError as exc:
        raise LauncherError(
            "FIFO_UNAVAILABLE_AFTER_ADMISSION"
        ) from exc

    if not stat.S_ISFIFO(
        fifo_stat.st_mode
    ):
        raise LauncherError(
            "FIFO_NOT_FIFO_AFTER_ADMISSION"
        )

    if (
        stat.S_IMODE(fifo_stat.st_mode)
        != 0o600
    ):
        raise LauncherError(
            "FIFO_MODE_INVALID_AFTER_ADMISSION"
        )

    return value


def show_contract():
    print(
        "PROMPT12_PRODUCTION_PROVIDER_MANAGER_LAUNCHER_CONTRACT=1"
    )
    print(f"SCHEMA={SCHEMA}")
    print(
        "MANAGER_START_NEW_SESSION=YES"
    )
    print(
        "MANAGER_STDIN=DEVNULL"
    )
    print(
        "MANAGER_STDOUT_STDERR=DEDICATED_EVIDENCE_FILES"
    )
    print(
        "MANAGER_SURVIVES_LAUNCHER_EXIT_AFTER_ADMISSION=YES"
    )
    print(
        "AUTOMATIC_RESTART=NO"
    )
    print(
        "ADMISSION_WAIT=BOUNDED"
    )
    print(
        "FAILURE_BEFORE_ADMISSION=TERMINATE_EXACT_MANAGER_PROCESS_GROUP"
    )
    print(
        "TRIGGER_WRITE_CAPABILITY=ABSENT"
    )
    print(
        "PRB_CONTROL_CAPABILITY=ABSENT"
    )
    print(
        "TRAFFIC_CAPABILITY=ABSENT"
    )
    print(
        "DOCKER_SPECIFIC_LOGIC=ABSENT"
    )
    print(
        "R01_IDENTITY_ALLOCATION_CAPABILITY=ABSENT"
    )


def run_launcher(args):
    allocation_path = absolute_file(
        args.allocation_json,
        "ALLOCATION_JSON",
    )

    launch_path = absolute_file(
        args.provider_launch_json,
        "PROVIDER_LAUNCH_JSON",
    )

    frozen_path = absolute_file(
        args.frozen_config,
        "FROZEN_CONFIG",
    )

    provider_source = absolute_file(
        args.provider_source,
        "PROVIDER_SOURCE",
    )

    record_path = new_absolute_file(
        args.launcher_record,
        "LAUNCHER_RECORD",
    )

    allocation = validate_allocation(
        allocation_path
    )

    validate_provider_launch(
        launch_path
    )

    timeout_ms, poll_ms = (
        validate_frozen_config(
            frozen_path
        )
    )

    stdout_path = (
        record_path.parent
        / "provider-manager.stdout.log"
    )

    stderr_path = (
        record_path.parent
        / "provider-manager.stderr.log"
    )

    for path, label in (
        (
            stdout_path,
            "PROVIDER_MANAGER_STDOUT",
        ),
        (
            stderr_path,
            "PROVIDER_MANAGER_STDERR",
        ),
    ):
        if os.path.lexists(str(path)):
            raise LauncherError(
                label + "_ALREADY_EXISTS"
            )

    command = [
        sys.executable,
        str(provider_source),
        "run",
        "--runtime-root",
        allocation["runtime_root"],
        "--fifo-path",
        allocation["fifo_path"],
        "--provider-launch-json",
        str(launch_path),
        "--provider-identity",
        allocation["provider_identity"],
        "--readiness-timeout-ms",
        str(timeout_ms),
        "--readiness-poll-ms",
        str(poll_ms),
        "--admission-authorization-token",
        AUTHORIZATION_TOKEN,
    ]

    process = None

    try:
        stdout_handle = stdout_path.open(
            "xb",
            buffering=0,
        )

        try:
            stderr_handle = stderr_path.open(
                "xb",
                buffering=0,
            )
        except Exception:
            stdout_handle.close()
            raise

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                close_fds=True,
                start_new_session=True,
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()

        manager_identity = (
            read_process_start_identity(
                process.pid
            )
        )

        runtime_root = pathlib.Path(
            allocation["runtime_root"]
        )

        admission_path = (
            runtime_root
            / "provider-admission.json"
        )

        deadline = (
            time.monotonic()
            + timeout_ms / 1000.0
        )

        while not admission_path.is_file():
            rc = process.poll()

            if rc is not None:
                raise LauncherError(
                    "PROVIDER_MANAGER_EXITED_BEFORE_ADMISSION:"
                    + str(rc)
                )

            if time.monotonic() >= deadline:
                raise LauncherError(
                    "PROVIDER_ADMISSION_TIMEOUT",
                    75,
                )

            time.sleep(
                poll_ms / 1000.0
            )

        admission = validate_admission(
            admission_path,
            allocation,
        )

        if process.poll() is not None:
            raise LauncherError(
                "PROVIDER_MANAGER_EXITED_AFTER_ADMISSION"
            )

        record = {
            "schema": SCHEMA,
            "launcher_completed_utc":
                utc_now(),
            "experiment_id":
                allocation["experiment_id"],
            "run_id":
                allocation["run_id"],
            "runtime_root":
                allocation["runtime_root"],
            "fifo_path":
                allocation["fifo_path"],
            "provider_identity":
                allocation["provider_identity"],
            "provider_source":
                str(provider_source),
            "provider_source_sha256":
                sha256_file(
                    provider_source
                ),
            "provider_launch_json":
                str(launch_path),
            "provider_launch_json_sha256":
                sha256_file(
                    launch_path
                ),
            "allocation_json":
                str(allocation_path),
            "allocation_json_sha256":
                sha256_file(
                    allocation_path
                ),
            "frozen_config":
                str(frozen_path),
            "frozen_config_sha256":
                sha256_file(
                    frozen_path
                ),
            "readiness_timeout_ms":
                timeout_ms,
            "readiness_poll_ms":
                poll_ms,
            "manager_pid":
                process.pid,
            "manager_process_start_identity":
                manager_identity,
            "provider_pid":
                admission["provider_pid"],
            "provider_process_start_identity":
                admission[
                    "provider_process_start_identity"
                ],
            "reader_readiness_gate":
                admission[
                    "reader_readiness_gate"
                ],
            "manager_start_new_session":
                True,
            "automatic_restart":
                False,
            "trigger_write_attempt_count":
                0,
            "control_executed":
                False,
            "traffic_executed":
                False,
        }

        write_json_exclusive(
            record_path,
            record,
        )

        print(
            json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
            )
        )

        return 0

    except Exception:
        terminate_manager(process)
        raise


def parse_args(argv=None):
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    commands.add_parser(
        "contract"
    )

    run = commands.add_parser(
        "run"
    )

    run.add_argument(
        "--allocation-json",
        required=True,
    )

    run.add_argument(
        "--provider-launch-json",
        required=True,
    )

    run.add_argument(
        "--frozen-config",
        required=True,
    )

    run.add_argument(
        "--provider-source",
        required=True,
    )

    run.add_argument(
        "--launcher-record",
        required=True,
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.command == "contract":
        show_contract()
        return 0

    if args.command == "run":
        return run_launcher(args)

    raise LauncherError(
        "COMMAND_INVALID"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LauncherError as exc:
        print(
            "PROMPT12_PROVIDER_MANAGER_LAUNCHER_GATE=FAIL "
            + "ERROR="
            + exc.reason,
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(exc.rc)
    except OSError as exc:
        print(
            "PROMPT12_PROVIDER_MANAGER_LAUNCHER_GATE=FAIL "
            + "ERROR=LOCAL_OPERATION_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc.errno),
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(74)
