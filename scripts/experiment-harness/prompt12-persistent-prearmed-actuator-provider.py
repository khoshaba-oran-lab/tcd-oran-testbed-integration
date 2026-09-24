#!/usr/bin/env python3
import argparse
import datetime
import errno
import hashlib
import json
import os
import pathlib
import re
import signal
import stat
import subprocess
import sys
import time


SCHEMA = (
    "sci_oran_prompt12_persistent_prearmed_"
    "actuator_provider_admission_v1"
)
AUTHORIZATION_TOKEN = "AUTHORISE_PROMPT12_PROVIDER_ADMISSION"
FIFO_TOKEN = "@PROMPT12_ACTUATOR_FIFO@"
IDENTITY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_termination_signal = None


class ProviderError(Exception):
    def __init__(self, reason, rc=65):
        super().__init__(reason)
        self.reason = reason
        self.rc = rc


def utc_now():
    return datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def nonempty(value, label):
    if not isinstance(value, str) or not value:
        raise ProviderError(label + "_INVALID")
    return value


def positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ProviderError(label + "_INVALID")
    if parsed <= 0 or parsed > 600000:
        raise ProviderError(label + "_INVALID")
    return parsed


def write_json_exclusive(path, value):
    path = pathlib.Path(path)
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(
                value,
                output,
                indent=2,
                sort_keys=True,
            )
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        path.chmod(0o640)
    except FileExistsError:
        raise ProviderError(
            "OUTPUT_ALREADY_EXISTS:" + str(path),
            73,
        )


def validate_runtime_root(value):
    root = pathlib.Path(
        nonempty(value, "RUNTIME_ROOT")
    )
    if not root.is_absolute():
        raise ProviderError("RUNTIME_ROOT_NOT_ABSOLUTE")
    try:
        parent = root.parent.resolve(strict=True)
    except OSError:
        raise ProviderError("RUNTIME_ROOT_PARENT_UNAVAILABLE")
    if parent != root.parent:
        raise ProviderError("RUNTIME_ROOT_PARENT_NOT_CANONICAL")
    if not parent.is_dir():
        raise ProviderError("RUNTIME_ROOT_PARENT_NOT_DIRECTORY")
    if os.path.lexists(str(root)):
        raise ProviderError("RUNTIME_ROOT_ALREADY_EXISTS", 73)
    return root


def validate_fifo_path(value, runtime_root):
    fifo = pathlib.Path(
        nonempty(value, "FIFO_PATH")
    )
    expected = runtime_root / "actuator.fifo"
    if not fifo.is_absolute():
        raise ProviderError("FIFO_PATH_NOT_ABSOLUTE")
    if fifo != expected:
        raise ProviderError("FIFO_PATH_NOT_CANONICAL")
    if os.path.lexists(str(fifo)):
        raise ProviderError("FIFO_PATH_ALREADY_EXISTS", 73)
    return fifo


def validate_launch_file(value):
    path = pathlib.Path(
        nonempty(value, "PROVIDER_LAUNCH_JSON")
    )
    if not path.is_absolute():
        raise ProviderError(
            "PROVIDER_LAUNCH_JSON_NOT_ABSOLUTE"
        )
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise ProviderError(
            "PROVIDER_LAUNCH_JSON_UNAVAILABLE"
        )
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ProviderError(
            "PROVIDER_LAUNCH_JSON_NOT_REGULAR_FILE"
        )
    return path


def load_launch_argv(path, fifo_path):
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        raise ProviderError(
            "PROVIDER_LAUNCH_JSON_INVALID"
        )
    if (
        not isinstance(value, list)
        or not value
        or not all(
            isinstance(item, str) and item
            for item in value
        )
    ):
        raise ProviderError(
            "PROVIDER_LAUNCH_ARGV_INVALID"
        )
    occurrences = sum(
        item.count(FIFO_TOKEN)
        for item in value
    )
    if occurrences != 1:
        raise ProviderError(
            "FIFO_TOKEN_OCCURRENCE_COUNT_INVALID"
        )
    expanded = [
        item.replace(FIFO_TOKEN, str(fifo_path))
        for item in value
    ]
    executable = pathlib.Path(expanded[0])
    if not executable.is_absolute():
        raise ProviderError(
            "PROVIDER_EXECUTABLE_NOT_ABSOLUTE"
        )
    if not executable.is_file():
        raise ProviderError(
            "PROVIDER_EXECUTABLE_NOT_REGULAR_FILE"
        )
    if not os.access(str(executable), os.X_OK):
        raise ProviderError(
            "PROVIDER_EXECUTABLE_NOT_EXECUTABLE"
        )
    encoded = json.dumps(
        expanded,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return expanded, hashlib.sha256(encoded).hexdigest()


def read_process_start_identity(pid):
    try:
        boot_id = pathlib.Path(
            "/proc/sys/kernel/random/boot_id"
        ).read_text(encoding="utf-8").strip()
        raw = pathlib.Path(
            f"/proc/{pid}/stat"
        ).read_text(encoding="utf-8")
    except OSError:
        raise ProviderError(
            "PROCESS_START_IDENTITY_UNAVAILABLE"
        )
    right_parenthesis = raw.rfind(")")
    if right_parenthesis < 0:
        raise ProviderError(
            "PROCESS_STAT_SHAPE_INVALID"
        )
    tail = raw[right_parenthesis + 2:].split()
    if len(tail) < 20:
        raise ProviderError(
            "PROCESS_STAT_SHAPE_INVALID"
        )
    start_ticks = tail[19]
    return f"{boot_id}:{pid}:{start_ticks}"


def terminate_exact_process_group(process):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def signal_handler(signum, _frame):
    global _termination_signal
    _termination_signal = signum


def parse_args():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    commands.add_parser("contract")
    run = commands.add_parser("run")
    run.add_argument("--runtime-root", required=True)
    run.add_argument("--fifo-path", required=True)
    run.add_argument(
        "--provider-launch-json",
        required=True,
    )
    run.add_argument(
        "--provider-identity",
        required=True,
    )
    run.add_argument(
        "--readiness-timeout-ms",
        required=True,
    )
    run.add_argument(
        "--readiness-poll-ms",
        required=True,
    )
    run.add_argument(
        "--admission-authorization-token",
        required=True,
    )
    return parser.parse_args()


def show_contract():
    print("PROMPT12_PERSISTENT_PREARMED_PROVIDER_CONTRACT=1")
    print(f"SCHEMA={SCHEMA}")
    print("COMMANDS=contract,run")
    print("RUNTIME_ROOT_CREATION=EXCLUSIVE")
    print("FIFO_CREATION=EXCLUSIVE")
    print("FIFO_MODE=0600")
    print("SHELL_EXECUTION_CAPABILITY=ABSENT")
    print("AUTOMATIC_RESTART=NO")
    print("READER_READINESS=NONBLOCKING_WRITER_OPEN_ZERO_BYTES")
    print("READINESS_WRITER_HELD_FOR_PROVIDER_LIFETIME=YES")
    print("TRIGGER_WRITE_CAPABILITY=ABSENT")
    print("PRB_CONTROL_CAPABILITY=ABSENT")
    print("TRAFFIC_CAPABILITY=ABSENT")
    print("DOCKER_SPECIFIC_LOGIC=ABSENT")
    print("CLEANUP_IS_SEPARATE_ACTION=YES")


def validate_run(args):
    if (
        args.admission_authorization_token
        != AUTHORIZATION_TOKEN
    ):
        raise ProviderError(
            "PROVIDER_ADMISSION_AUTHORIZATION_INVALID",
            77,
        )
    runtime_root = validate_runtime_root(
        args.runtime_root
    )
    fifo_path = validate_fifo_path(
        args.fifo_path,
        runtime_root,
    )
    launch_path = validate_launch_file(
        args.provider_launch_json
    )
    provider_identity = nonempty(
        args.provider_identity,
        "PROVIDER_IDENTITY",
    )
    if not IDENTITY_PATTERN.fullmatch(
        provider_identity
    ):
        raise ProviderError(
            "PROVIDER_IDENTITY_INVALID"
        )
    timeout_ms = positive_int(
        args.readiness_timeout_ms,
        "READINESS_TIMEOUT_MS",
    )
    poll_ms = positive_int(
        args.readiness_poll_ms,
        "READINESS_POLL_MS",
    )
    if poll_ms > timeout_ms:
        raise ProviderError(
            "READINESS_POLL_EXCEEDS_TIMEOUT"
        )
    argv, argv_sha256 = load_launch_argv(
        launch_path,
        fifo_path,
    )
    return {
        "runtime_root": runtime_root,
        "fifo_path": fifo_path,
        "provider_identity": provider_identity,
        "timeout_ms": timeout_ms,
        "poll_ms": poll_ms,
        "argv": argv,
        "argv_sha256": argv_sha256,
    }


def failure_record(
    runtime_root,
    fifo_path,
    provider_identity,
    child,
    reason,
):
    if (
        runtime_root is None
        or not runtime_root.is_dir()
    ):
        return
    value = {
        "schema": SCHEMA,
        "state": "FAILED",
        "failure_reason": reason,
        "failure_utc": utc_now(),
        "execution_host": os.uname().nodename,
        "runtime_root": str(runtime_root),
        "fifo_path": (
            str(fifo_path)
            if fifo_path is not None
            else None
        ),
        "fifo_exists": (
            os.path.lexists(str(fifo_path))
            if fifo_path is not None
            else False
        ),
        "provider_identity": provider_identity,
        "provider_pid": (
            child.pid
            if child is not None
            else None
        ),
        "provider_restart_count": 0,
        "automatic_retry": False,
        "runtime_paths_removed": False,
        "trigger_write_attempt_count": 0,
        "control_executed": False,
        "traffic_executed": False,
    }
    path = runtime_root / "provider-failure.json"
    try:
        write_json_exclusive(path, value)
    except (ProviderError, OSError):
        pass


def run_provider(args):
    global _termination_signal
    _termination_signal = None

    runtime_root = None
    fifo_path = None
    provider_identity = None
    child = None
    readiness_fd = None

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        values = validate_run(args)
        runtime_root = values["runtime_root"]
        fifo_path = values["fifo_path"]
        provider_identity = values[
            "provider_identity"
        ]

        os.mkdir(str(runtime_root), mode=0o750)
        runtime_root.chmod(0o750)

        os.mkfifo(str(fifo_path), mode=0o600)
        fifo_path.chmod(0o600)

        stdout_path = (
            runtime_root / "provider.stdout.log"
        )
        stderr_path = (
            runtime_root / "provider.stderr.log"
        )
        stdout_handle = stdout_path.open("xb", buffering=0)
        try:
            stderr_handle = stderr_path.open(
                "xb",
                buffering=0,
            )
        except Exception:
            stdout_handle.close()
            raise

        try:
            child = subprocess.Popen(
                values["argv"],
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

        start_identity = read_process_start_identity(
            child.pid
        )

        deadline = (
            time.monotonic()
            + values["timeout_ms"] / 1000.0
        )
        open_flags = os.O_WRONLY | os.O_NONBLOCK
        if hasattr(os, "O_CLOEXEC"):
            open_flags |= os.O_CLOEXEC

        while readiness_fd is None:
            if _termination_signal is not None:
                raise ProviderError(
                    "TERMINATION_REQUESTED_BEFORE_ADMISSION",
                    75,
                )
            child_rc = child.poll()
            if child_rc is not None:
                raise ProviderError(
                    "PROVIDER_EXITED_BEFORE_READINESS:"
                    + str(child_rc)
                )
            try:
                readiness_fd = os.open(
                    str(fifo_path),
                    open_flags,
                )
            except OSError as exc:
                if exc.errno not in (
                    errno.ENXIO,
                    errno.EAGAIN,
                ):
                    raise ProviderError(
                        "READER_READINESS_OPEN_FAILED:"
                        + str(exc.errno)
                    )
            if readiness_fd is not None:
                break
            if time.monotonic() >= deadline:
                raise ProviderError(
                    "READER_READINESS_TIMEOUT"
                )
            time.sleep(
                values["poll_ms"] / 1000.0
            )

        fifo_stat = fifo_path.stat()
        admission = {
            "schema": SCHEMA,
            "state": "ADMITTED",
            "execution_host": os.uname().nodename,
            "runtime_root": str(runtime_root),
            "fifo_path": str(fifo_path),
            "fifo_mode": format(
                stat.S_IMODE(fifo_stat.st_mode),
                "04o",
            ),
            "fifo_uid": fifo_stat.st_uid,
            "fifo_gid": fifo_stat.st_gid,
            "provider_identity": provider_identity,
            "provider_pid": child.pid,
            "provider_process_start_identity":
                start_identity,
            "provider_restart_count": 0,
            "provider_launch_argv_sha256":
                values["argv_sha256"],
            "reader_readiness_gate": "PASS",
            "readiness_method":
                "O_WRONLY_NONBLOCK_ZERO_BYTE_OPEN",
            "readiness_writer_fd_held": True,
            "trigger_write_attempt_count": 0,
            "trigger_write_success_count": 0,
            "control_executed": False,
            "traffic_executed": False,
            "admission_utc": utc_now(),
        }
        write_json_exclusive(
            runtime_root / "provider-admission.json",
            admission,
        )
        sys.stdout.write(
            json.dumps(
                admission,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        sys.stdout.flush()

        while child.poll() is None:
            if _termination_signal is not None:
                terminate_exact_process_group(child)
                return 0
            time.sleep(0.05)

        return child.returncode or 0

    except ProviderError as exc:
        terminate_exact_process_group(child)
        failure_record(
            runtime_root,
            fifo_path,
            provider_identity,
            child,
            exc.reason,
        )
        raise
    except OSError as exc:
        terminate_exact_process_group(child)
        error = ProviderError(
            "LOCAL_OPERATION_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc.errno)
        )
        failure_record(
            runtime_root,
            fifo_path,
            provider_identity,
            child,
            error.reason,
        )
        raise error
    finally:
        if readiness_fd is not None:
            try:
                os.close(readiness_fd)
            except OSError:
                pass


def main():
    args = parse_args()
    if args.command == "contract":
        show_contract()
        return 0
    try:
        return run_provider(args)
    except ProviderError as exc:
        print(
            "PROMPT12_PERSISTENT_PREARMED_PROVIDER_GATE=FAIL",
            file=sys.stderr,
        )
        print(
            "FAIL_REASON=" + exc.reason,
            file=sys.stderr,
        )
        print("CONTROL_EXECUTED=NO", file=sys.stderr)
        print(
            "SCIENTIFIC_TRIGGER_EXECUTED=NO",
            file=sys.stderr,
        )
        return exc.rc


if __name__ == "__main__":
    raise SystemExit(main())
