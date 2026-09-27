#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import pathlib
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


HERE = pathlib.Path(__file__).resolve().parent

WRAPPER_PATH = (
    HERE.parent
    / "prompt12-production-actuator-wrapper.py"
)

SPEC = importlib.util.spec_from_file_location(
    "prompt12_production_actuator_wrapper",
    WRAPPER_PATH,
)

MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


class FakeDocker:
    def __init__(
        self,
        *,
        image_rc=0,
        network_rc=0,
        run_rc=0,
        run_stdout="actuator-ok\n",
        run_stderr="",
    ):
        self.image_rc = image_rc
        self.network_rc = network_rc
        self.run_rc = run_rc
        self.run_stdout = run_stdout
        self.run_stderr = run_stderr
        self.calls = []

    def __call__(
        self,
        argv,
        *,
        shell,
        check,
        capture_output,
        text,
    ):
        self.calls.append(
            list(argv)
        )

        if argv[1:3] == [
            "image",
            "inspect",
        ]:
            return subprocess.CompletedProcess(
                argv,
                self.image_rc,
                stdout="image\n" if self.image_rc == 0 else "",
                stderr="" if self.image_rc == 0 else "missing image\n",
            )

        if argv[1:3] == [
            "network",
            "inspect",
        ]:
            return subprocess.CompletedProcess(
                argv,
                self.network_rc,
                stdout="network\n" if self.network_rc == 0 else "",
                stderr="" if self.network_rc == 0 else "missing network\n",
            )

        if argv[1] == "run":
            return subprocess.CompletedProcess(
                argv,
                self.run_rc,
                stdout=self.run_stdout,
                stderr=self.run_stderr,
            )

        raise AssertionError(
            "UNEXPECTED_DOCKER_COMMAND="
            + repr(argv)
        )

    @property
    def run_calls(self):
        return [
            call
            for call in self.calls
            if len(call) >= 2
            and call[1] == "run"
        ]


class ProductionActuatorWrapperTests(
    unittest.TestCase
):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(
            self.tmp.name
        )

        self.actuator = (
            self.root
            / "canonical-actuator"
        )

        self.config = (
            self.root
            / "ric.conf"
        )

        self.actuator_bytes = (
            b"fake-actuator-v1\n"
        )

        self.config_bytes = (
            b"[ric]\n"
            b"fake=true\n"
        )

        self.actuator.write_bytes(
            self.actuator_bytes
        )

        self.config.write_bytes(
            self.config_bytes
        )

        self.actuator.chmod(
            stat.S_IRUSR
            | stat.S_IWUSR
            | stat.S_IXUSR
        )

        self.config.chmod(
            stat.S_IRUSR
            | stat.S_IWUSR
        )

        self.actuator_sha = sha256_bytes(
            self.actuator_bytes
        )

        self.config_sha = sha256_bytes(
            self.config_bytes
        )

        self.patchers = [
            mock.patch.object(
                MOD,
                "ACTUATOR_BINARY_SOURCE",
                self.actuator,
            ),
            mock.patch.object(
                MOD,
                "ACTUATOR_BINARY_SHA256",
                self.actuator_sha,
            ),
            mock.patch.object(
                MOD,
                "XAPP_CONFIG_SOURCE",
                self.config,
            ),
            mock.patch.object(
                MOD,
                "XAPP_CONFIG_SHA256",
                self.config_sha,
            ),
        ]

        for patcher in self.patchers:
            patcher.start()

        self.docker = (
            "/usr/bin/docker"
        )

        self.invocation_id = (
            "test-invocation-001"
        )

    def tearDown(self):
        for patcher in reversed(
            self.patchers
        ):
            patcher.stop()

        self.tmp.cleanup()

    def execute(
        self,
        ratio="50",
        fake=None,
        invocation_id=None,
    ):
        if fake is None:
            fake = FakeDocker()

        if invocation_id is None:
            invocation_id = (
                self.invocation_id
            )

        return MOD.execute(
            environ={
                MOD.RATIO_ENV: ratio,
            },
            runner=fake,
            docker_path=self.docker,
            invocation_id=invocation_id,
        )

    def test_missing_ratio_fails_closed_before_docker(self):
        fake = FakeDocker()

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "RATIO_ENV_MISSING",
        ):
            MOD.execute(
                environ={},
                runner=fake,
                docker_path=self.docker,
                invocation_id=self.invocation_id,
            )

        self.assertEqual(
            fake.calls,
            [],
        )

    def test_invalid_ratio_fails_closed_before_docker(self):
        fake = FakeDocker()

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "RATIO_ENV_INVALID",
        ):
            MOD.execute(
                environ={
                    MOD.RATIO_ENV: "60",
                },
                runner=fake,
                docker_path=self.docker,
                invocation_id=self.invocation_id,
            )

        self.assertEqual(
            fake.calls,
            [],
        )

    def test_all_allowed_ratios_are_accepted(self):
        for ratio in (
            "25",
            "50",
            "75",
            "100",
        ):
            with self.subTest(
                ratio=ratio
            ):
                fake = FakeDocker()

                evidence, rc = self.execute(
                    ratio=ratio,
                    fake=fake,
                    invocation_id=(
                        "ratio-"
                        + ratio
                    ),
                )

                self.assertEqual(
                    rc,
                    0,
                )

                self.assertEqual(
                    evidence[
                        "requested_ratio_pct"
                    ],
                    int(ratio),
                )

                self.assertEqual(
                    len(fake.run_calls),
                    1,
                )

    def test_binary_identity_mismatch_fails_closed(self):
        fake = FakeDocker()

        self.actuator.write_bytes(
            b"tampered\n"
        )

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "ACTUATOR_BINARY_SHA256_MISMATCH",
        ):
            self.execute(
                fake=fake
            )

        self.assertEqual(
            fake.calls,
            [],
        )

    def test_config_identity_mismatch_fails_closed(self):
        fake = FakeDocker()

        self.config.write_bytes(
            b"tampered-config\n"
        )

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "XAPP_CONFIG_SHA256_MISMATCH",
        ):
            self.execute(
                fake=fake
            )

        self.assertEqual(
            fake.calls,
            [],
        )

    def test_missing_image_fails_without_run_attempt(self):
        fake = FakeDocker(
            image_rc=1
        )

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "DOCKER_IMAGE_MISSING",
        ):
            self.execute(
                fake=fake
            )

        self.assertEqual(
            len(fake.run_calls),
            0,
        )

        self.assertEqual(
            len(fake.calls),
            1,
        )

    def test_missing_network_fails_without_run_attempt(self):
        fake = FakeDocker(
            network_rc=1
        )

        with self.assertRaisesRegex(
            MOD.WrapperError,
            "DOCKER_NETWORK_MISSING",
        ):
            self.execute(
                fake=fake
            )

        self.assertEqual(
            len(fake.run_calls),
            0,
        )

        self.assertEqual(
            len(fake.calls),
            2,
        )

    def test_exact_docker_run_argv(self):
        fake = FakeDocker()

        evidence, rc = self.execute(
            fake=fake
        )

        self.assertEqual(
            rc,
            0,
        )

        expected = [
            self.docker,
            "run",
            "--name",
            (
                MOD.CONTAINER_PREFIX
                + "-"
                + self.invocation_id
            ),
            "--network",
            MOD.EXECUTION_NETWORK,
            "--restart",
            "no",
            "--security-opt",
            "no-new-privileges",
            "--env",
            "SCI_ORAN_MAX_PRB_RATIO=50",
            "--mount",
            (
                "type=bind,"
                "src="
                + str(self.actuator)
                + ",dst="
                + MOD.ACTUATOR_BINARY_DESTINATION
                + ",readonly"
            ),
            "--mount",
            (
                "type=bind,"
                "src="
                + str(self.config)
                + ",dst="
                + MOD.XAPP_CONFIG_DESTINATION
                + ",readonly"
            ),
            "--entrypoint",
            MOD.ACTUATOR_ENTRYPOINT,
            MOD.EXECUTION_IMAGE,
            "-c",
            "/opt/action11r/xapp_oran_sm.conf",
        ]

        self.assertEqual(
            fake.run_calls,
            [expected],
        )

        self.assertEqual(
            evidence["docker_argv"],
            expected,
        )

    def test_ratio_environment_is_propagated_exactly_once(self):
        fake = FakeDocker()

        evidence, rc = self.execute(
            ratio="75",
            fake=fake,
        )

        self.assertEqual(
            rc,
            0,
        )

        argv = fake.run_calls[0]

        self.assertEqual(
            argv.count("--env"),
            1,
        )

        self.assertEqual(
            argv.count(
                "SCI_ORAN_MAX_PRB_RATIO=75"
            ),
            1,
        )

        self.assertEqual(
            evidence[
                "requested_ratio_pct"
            ],
            75,
        )

    def test_mounts_are_read_only(self):
        fake = FakeDocker()

        self.execute(
            fake=fake
        )

        argv = fake.run_calls[0]

        mounts = [
            argv[index + 1]
            for index, value
            in enumerate(argv)
            if value == "--mount"
        ]

        self.assertEqual(
            len(mounts),
            2,
        )

        for mount in mounts:
            self.assertTrue(
                mount.endswith(
                    ",readonly"
                )
            )

    def test_exact_entrypoint_and_config_argument(self):
        fake = FakeDocker()

        self.execute(
            fake=fake
        )

        argv = fake.run_calls[0]

        entrypoint_index = (
            argv.index(
                "--entrypoint"
            )
        )

        self.assertEqual(
            argv[
                entrypoint_index + 1
            ],
            "/opt/action11r/canonical-actuator",
        )

        image_index = argv.index(
            MOD.EXECUTION_IMAGE
        )

        self.assertEqual(
            argv[
                image_index + 1:
            ],
            [
                "-c",
                "/opt/action11r/xapp_oran_sm.conf",
            ],
        )

    def test_auto_remove_is_not_enabled(self):
        fake = FakeDocker()

        self.execute(
            fake=fake
        )

        argv = fake.run_calls[0]

        self.assertNotIn(
            "--rm",
            argv,
        )

        self.assertIs(
            MOD.AUTO_REMOVE,
            False,
        )

    def test_one_invocation_has_one_docker_run_attempt(self):
        fake = FakeDocker()

        evidence, rc = self.execute(
            fake=fake
        )

        self.assertEqual(
            rc,
            0,
        )

        self.assertEqual(
            len(fake.run_calls),
            1,
        )

        self.assertEqual(
            evidence[
                "docker_execution_attempt_count"
            ],
            1,
        )

        self.assertIs(
            evidence[
                "automatic_retry"
            ],
            False,
        )

        self.assertEqual(
            evidence[
                "control_request_expected_count"
            ],
            1,
        )

    def test_nonzero_actuator_status_propagates(self):
        fake = FakeDocker(
            run_rc=37,
            run_stdout="",
            run_stderr="actuator-failed\n",
        )

        evidence, rc = self.execute(
            fake=fake
        )

        self.assertEqual(
            rc,
            37,
        )

        self.assertEqual(
            len(fake.run_calls),
            1,
        )

        self.assertEqual(
            evidence["gate"],
            "FAIL",
        )

        self.assertEqual(
            evidence["error"],
            "ACTUATOR_EXECUTION_FAILED",
        )

        self.assertEqual(
            evidence[
                "docker_returncode"
            ],
            37,
        )

    def test_machine_readable_evidence_is_deterministic(self):
        fake_a = FakeDocker()
        fake_b = FakeDocker()

        evidence_a, rc_a = self.execute(
            fake=fake_a
        )

        evidence_b, rc_b = self.execute(
            fake=fake_b
        )

        self.assertEqual(
            rc_a,
            0,
        )

        self.assertEqual(
            rc_b,
            0,
        )

        encoded_a = json.dumps(
            evidence_a,
            sort_keys=True,
            separators=(",", ":"),
        )

        encoded_b = json.dumps(
            evidence_b,
            sort_keys=True,
            separators=(",", ":"),
        )

        self.assertEqual(
            encoded_a,
            encoded_b,
        )

        decoded = json.loads(
            encoded_a
        )

        self.assertEqual(
            decoded["schema"],
            MOD.SCHEMA,
        )

        self.assertEqual(
            decoded["gate"],
            "PASS",
        )

        self.assertEqual(
            decoded["invocation_id"],
            self.invocation_id,
        )

    def test_failure_evidence_has_zero_execution_attempts(self):
        evidence = MOD.failure_evidence(
            "TEST_FAILURE"
        )

        self.assertEqual(
            evidence["gate"],
            "FAIL",
        )

        self.assertEqual(
            evidence["error"],
            "TEST_FAILURE",
        )

        self.assertEqual(
            evidence[
                "docker_execution_attempt_count"
            ],
            0,
        )

        self.assertIs(
            evidence[
                "automatic_retry"
            ],
            False,
        )


if __name__ == "__main__":
    unittest.main()
