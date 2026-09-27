#!/usr/bin/env python3

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import uuid


SCHEMA = "sci_oran_prompt12_v2_production_actuator_wrapper_evidence_v1"

RATIO_ENV = "SCI_ORAN_MAX_PRB_RATIO"
ALLOWED_RATIOS = ("25", "50", "75", "100")

EXECUTION_IMAGE = (
    "sha256:"
    "02a7181afaf1cb5892bbaaaeb3808e9db9bcb7594fa48396e3da56e210bc60bb"
)

EXECUTION_NETWORK = "tcd-base05-zmq_ran"

ACTUATOR_BINARY_SOURCE = pathlib.Path(
    "/home/khoshaba/sci-oran/build/"
    "prompt12-actuator-bfd1a35b/build/examples/xApp/c/control/"
    "xapp_oran_slice_ctrl"
)

ACTUATOR_BINARY_SHA256 = (
    "de71dcc0298c50c433828ec80be60bd68447ad6ef2912b2dcf3da65e10d4700f"
)

ACTUATOR_BINARY_DESTINATION = "/opt/action11r/canonical-actuator"

XAPP_CONFIG_SOURCE = pathlib.Path(
    "/home/khoshaba/project/tcd-oran-testbed-integration/"
    "deploy/phase-2-flexric/tb3-runtime/configs/ric.conf"
)

XAPP_CONFIG_SHA256 = (
    "940d8e1a87b8e937fea3678ca9fc47dd765f3bdf9f68f731cf6d2d47dda8be68"
)

XAPP_CONFIG_DESTINATION = "/opt/action11r/xapp_oran_sm.conf"

ACTUATOR_ENTRYPOINT = "/opt/action11r/canonical-actuator"
ACTUATOR_ARGUMENTS = ("-c", "/opt/action11r/xapp_oran_sm.conf")

RESTART_POLICY = "no"
SECURITY_OPT = "no-new-privileges"
AUTO_REMOVE = False

CONTAINER_PREFIX = "prompt12-siso-actuator-v2"


class WrapperError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_ratio(environ):
    raw = environ.get(RATIO_ENV)

    if raw is None:
        raise WrapperError("RATIO_ENV_MISSING")

    if raw not in ALLOWED_RATIOS:
        raise WrapperError("RATIO_ENV_INVALID")

    return raw


def validate_regular_file_identity(
    path,
    expected_sha256,
    require_executable,
    label,
):
    if not path.is_absolute():
        raise WrapperError(label + "_PATH_NOT_ABSOLUTE")

    if not path.exists():
        raise WrapperError(label + "_MISSING")

    if path.is_symlink():
        raise WrapperError(label + "_SYMLINK_PROHIBITED")

    if not path.is_file():
        raise WrapperError(label + "_NOT_REGULAR_FILE")

    if require_executable and not os.access(path, os.X_OK):
        raise WrapperError(label + "_NOT_EXECUTABLE")

    actual = sha256_file(path)

    if actual != expected_sha256:
        raise WrapperError(label + "_SHA256_MISMATCH")

    return actual


def resolve_docker():
    value = shutil.which("docker")

    if value is None:
        raise WrapperError("DOCKER_CLIENT_MISSING")

    path = pathlib.Path(value)

    if not path.is_absolute():
        raise WrapperError("DOCKER_CLIENT_PATH_NOT_ABSOLUTE")

    if not path.is_file():
        raise WrapperError("DOCKER_CLIENT_NOT_REGULAR_FILE")

    if not os.access(path, os.X_OK):
        raise WrapperError("DOCKER_CLIENT_NOT_EXECUTABLE")

    return str(path)


def run_probe(runner, argv, failure_code):
    result = runner(
        argv,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise WrapperError(failure_code)

    return result


def validate_image_and_network(runner, docker):
    run_probe(
        runner,
        [
            docker,
            "image",
            "inspect",
            EXECUTION_IMAGE,
        ],
        "DOCKER_IMAGE_MISSING",
    )

    run_probe(
        runner,
        [
            docker,
            "network",
            "inspect",
            EXECUTION_NETWORK,
        ],
        "DOCKER_NETWORK_MISSING",
    )


def validate_invocation_id(value):
    if not isinstance(value, str):
        raise WrapperError("INVOCATION_ID_INVALID")

    if not value:
        raise WrapperError("INVOCATION_ID_INVALID")

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_"
    )

    if any(ch not in allowed for ch in value):
        raise WrapperError("INVOCATION_ID_INVALID")

    if len(value) > 48:
        raise WrapperError("INVOCATION_ID_INVALID")

    return value


def generate_invocation_id():
    return uuid.uuid4().hex


def container_name(invocation_id):
    invocation_id = validate_invocation_id(invocation_id)
    return CONTAINER_PREFIX + "-" + invocation_id


def readonly_bind_mount(source, destination):
    return (
        "type=bind,"
        "src=" + str(source) + ","
        "dst=" + destination + ","
        "readonly"
    )


def build_docker_run_argv(
    docker,
    ratio,
    invocation_id,
):
    name = container_name(invocation_id)

    argv = [
        docker,
        "run",
        "--name",
        name,
        "--network",
        EXECUTION_NETWORK,
        "--restart",
        RESTART_POLICY,
        "--security-opt",
        SECURITY_OPT,
        "--env",
        RATIO_ENV + "=" + ratio,
        "--mount",
        readonly_bind_mount(
            ACTUATOR_BINARY_SOURCE,
            ACTUATOR_BINARY_DESTINATION,
        ),
        "--mount",
        readonly_bind_mount(
            XAPP_CONFIG_SOURCE,
            XAPP_CONFIG_DESTINATION,
        ),
        "--entrypoint",
        ACTUATOR_ENTRYPOINT,
        EXECUTION_IMAGE,
        *ACTUATOR_ARGUMENTS,
    ]

    if AUTO_REMOVE:
        raise WrapperError("AUTO_REMOVE_CONTRACT_VIOLATION")

    return argv


def base_evidence(
    ratio,
    invocation_id,
    docker,
    actuator_sha,
    config_sha,
):
    return {
        "schema": SCHEMA,
        "gate": "PENDING",
        "error": None,
        "requested_ratio_pct": int(ratio),
        "ratio_env": RATIO_ENV,
        "invocation_id": invocation_id,
        "container_name": container_name(invocation_id),
        "execution_image": EXECUTION_IMAGE,
        "execution_network": EXECUTION_NETWORK,
        "actuator_binary_source": str(ACTUATOR_BINARY_SOURCE),
        "actuator_binary_sha256": actuator_sha,
        "actuator_binary_destination": ACTUATOR_BINARY_DESTINATION,
        "xapp_config_source": str(XAPP_CONFIG_SOURCE),
        "xapp_config_sha256": config_sha,
        "xapp_config_destination": XAPP_CONFIG_DESTINATION,
        "actuator_entrypoint": ACTUATOR_ENTRYPOINT,
        "actuator_arguments": list(ACTUATOR_ARGUMENTS),
        "restart_policy": RESTART_POLICY,
        "security_opt": SECURITY_OPT,
        "auto_remove": AUTO_REMOVE,
        "docker_path": docker,
        "docker_execution_attempt_count": 0,
        "automatic_retry": False,
        "control_request_expected_count": 1,
        "docker_returncode": None,
        "docker_stdout": "",
        "docker_stderr": "",
        "docker_argv": [],
    }


def execute(
    *,
    environ=None,
    runner=subprocess.run,
    docker_path=None,
    invocation_id=None,
):
    if environ is None:
        environ = os.environ

    ratio = validate_ratio(environ)

    actuator_sha = validate_regular_file_identity(
        ACTUATOR_BINARY_SOURCE,
        ACTUATOR_BINARY_SHA256,
        True,
        "ACTUATOR_BINARY",
    )

    config_sha = validate_regular_file_identity(
        XAPP_CONFIG_SOURCE,
        XAPP_CONFIG_SHA256,
        False,
        "XAPP_CONFIG",
    )

    if docker_path is None:
        docker = resolve_docker()
    else:
        docker = str(docker_path)

    if not pathlib.Path(docker).is_absolute():
        raise WrapperError("DOCKER_CLIENT_PATH_NOT_ABSOLUTE")

    validate_image_and_network(
        runner,
        docker,
    )

    if invocation_id is None:
        invocation_id = generate_invocation_id()

    invocation_id = validate_invocation_id(
        invocation_id
    )

    argv = build_docker_run_argv(
        docker,
        ratio,
        invocation_id,
    )

    evidence = base_evidence(
        ratio,
        invocation_id,
        docker,
        actuator_sha,
        config_sha,
    )

    evidence["docker_argv"] = list(argv)
    evidence["docker_execution_attempt_count"] = 1

    result = runner(
        argv,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
    )

    evidence["docker_returncode"] = result.returncode
    evidence["docker_stdout"] = result.stdout
    evidence["docker_stderr"] = result.stderr

    if result.returncode == 0:
        evidence["gate"] = "PASS"
    else:
        evidence["gate"] = "FAIL"
        evidence["error"] = "ACTUATOR_EXECUTION_FAILED"

    return evidence, result.returncode


def failure_evidence(code):
    return {
        "schema": SCHEMA,
        "gate": "FAIL",
        "error": code,
        "docker_execution_attempt_count": 0,
        "automatic_retry": False,
        "control_request_expected_count": 1,
    }


def emit(evidence):
    print(
        json.dumps(
            evidence,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def main():
    try:
        evidence, returncode = execute()
    except WrapperError as exc:
        emit(
            failure_evidence(
                exc.code
            )
        )
        return 2

    emit(evidence)

    if returncode == 0:
        return 0

    return returncode


if __name__ == "__main__":
    sys.exit(main())
