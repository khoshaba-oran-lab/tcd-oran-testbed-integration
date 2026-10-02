#!/usr/bin/env python3

import os
import pathlib
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]

PREFLIGHT = (
    ROOT
    / "scripts"
    / "experiment-harness"
    / "lib"
    / "preflight.sh"
)

RUNNER = (
    ROOT
    / "scripts"
    / "experiment-harness"
    / "run-experiment.sh"
)


class GenericPreflightTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="r6h-generic-preflight-"
        )

        self.root = pathlib.Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.fakebin = self.root / "fakebin"

        self.repo.mkdir()
        self.fakebin.mkdir()

        (self.repo / ".git").mkdir()

        scripts = self.repo / "scripts"
        harness = scripts / "experiment-harness"

        scripts.mkdir(exist_ok=True)
        harness.mkdir(
            parents=True,
            exist_ok=True,
        )

        (
            scripts
            / "tb3-resource-network-observer.py"
        ).write_text(
            "# test fixture\n",
            encoding="utf-8",
        )

        receiver = (
            scripts
            / "tb3-native-metrics-receiver.sh"
        )

        receiver.write_text(
            "#!/bin/sh\nexit 0\n",
            encoding="utf-8",
        )

        receiver.chmod(0o755)

        doctor = scripts / "sci-oran-doctor.sh"

        doctor.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                if [ "${FAKE_DOCTOR_MODE:-pass}" = "fail" ]; then
                    echo "SCI_ORAN_READY_GATE=FAIL"
                    echo "FAILURE_REASON=TEST_PLATFORM_FAILURE"
                    exit 70
                fi

                echo "SCI_ORAN_READY_GATE=PASS"
                echo "FAILURE_REASON=NONE"
                exit 0
                """
            ),
            encoding="utf-8",
        )

        doctor.chmod(0o755)

        provider = (
            harness
            / "r6-f-portable-runtime-preflight.py"
        )

        provider.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh

                if [ -n "${FAKE_PROVIDER_SENTINEL:-}" ]; then
                    printf 'CALLED\\n' > "$FAKE_PROVIDER_SENTINEL"
                fi

                output=""

                while [ "$#" -gt 0 ]; do
                    case "$1" in
                        --python-executable)
                            shift
                            python_executable="$1"
                            ;;
                        --require-jsonschema)
                            shift
                            require_jsonschema="$1"
                            ;;
                        --output)
                            shift
                            output="$1"
                            ;;
                        *)
                            exit 64
                            ;;
                    esac
                    shift
                done

                mode="${FAKE_PORTABLE_MODE:-pass}"

                if [ "$mode" = "nonzero" ]; then
                    echo "R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=FAIL"
                    echo "ADMISSION_QUALIFICATION_GATE=FAIL"
                    exit 17
                fi

                if [ "$mode" = "nonpass" ]; then
                    printf '{}\\n' > "$output"
                    echo "R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=FAIL"
                    echo "ADMISSION_QUALIFICATION_GATE=FAIL"
                    exit 0
                fi

                printf '{}\\n' > "$output"

                echo "R6_F_PORTABLE_RUNTIME_PREFLIGHT_GATE=PASS"
                echo "ADMISSION_QUALIFICATION_GATE=PASS"
                exit 0
                """
            ),
            encoding="utf-8",
        )

        provider.chmod(0o755)

        self._write_fake_command(
            "git",
            "#!/bin/sh\nexit 0\n",
        )

        self._write_fake_command(
            "python3",
            "#!/bin/sh\nexit 0\n",
        )

        self._write_fake_command(
            "sha256sum",
            "#!/bin/sh\nexit 0\n",
        )

        self._write_fake_command(
            "docker",
            textwrap.dedent(
                """\
                #!/bin/sh
                if [ "${1:-}" = "info" ]; then
                    exit 0
                fi
                exit 0
                """
            ),
        )

        self._write_fake_command(
            "ip",
            textwrap.dedent(
                """\
                #!/bin/sh
                echo "tb3test UP 10.53.1.1/24"
                exit 0
                """
            ),
        )

        self._write_fake_command(
            "ss",
            "#!/bin/sh\nexit 0\n",
        )

        self.output = (
            self.root
            / "portable-admission.json"
        )

        self.sentinel = (
            self.root
            / "provider-called.txt"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_fake_command(self, name, content):
        path = self.fakebin / name

        path.write_text(
            content,
            encoding="utf-8",
        )

        path.chmod(0o755)

    def run_precheck(
        self,
        *,
        doctor_mode="pass",
        portable_mode="pass",
        python_executable="/bin/sh",
        require_jsonschema="yes",
        output_path=None,
        omit=(),
    ):
        if output_path is None:
            output_path = self.output

        env = os.environ.copy()

        env["PATH"] = (
            str(self.fakebin)
            + os.pathsep
            + env.get("PATH", "")
        )

        env["FAKE_DOCTOR_MODE"] = doctor_mode
        env["FAKE_PORTABLE_MODE"] = portable_mode
        env["FAKE_PROVIDER_SENTINEL"] = str(
            self.sentinel
        )

        values = {
            "SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE":
                python_executable,
            "SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA":
                require_jsonschema,
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT":
                str(output_path),
        }

        for key, value in values.items():
            if key not in omit:
                env[key] = value
            else:
                env.pop(key, None)

        return subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; sci_oran_precheck "$2"',
                "bash",
                str(PREFLIGHT),
                str(self.repo),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            check=False,
        )

    def test_platform_fail_short_circuits_portable_provider(self):
        proc = self.run_precheck(
            doctor_mode="fail"
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "SCI_ORAN_PREFLIGHT_READY_GATE=FAIL",
            proc.stderr,
        )

        self.assertIn(
            "TEST_PLATFORM_FAILURE",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_missing_python_binding_fails(self):
        proc = self.run_precheck(
            omit={
                "SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE"
            }
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "MISSING_PREFLIGHT_PYTHON_EXECUTABLE",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_missing_jsonschema_policy_binding_fails(self):
        proc = self.run_precheck(
            omit={
                "SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA"
            }
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "MISSING_PREFLIGHT_REQUIRE_JSONSCHEMA",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_missing_output_binding_fails(self):
        proc = self.run_precheck(
            omit={
                "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT"
            }
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "MISSING_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_invalid_jsonschema_policy_binding_fails(self):
        proc = self.run_precheck(
            require_jsonschema="maybe"
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "PREFLIGHT_REQUIRE_JSONSCHEMA_INVALID",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_nonabsolute_python_binding_fails(self):
        proc = self.run_precheck(
            python_executable="python3"
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "PREFLIGHT_PYTHON_EXECUTABLE_NOT_ABSOLUTE",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_nonexecutable_python_binding_fails(self):
        nonexec = self.root / "not-executable"

        nonexec.write_text(
            "#!/bin/sh\n",
            encoding="utf-8",
        )

        proc = self.run_precheck(
            python_executable=str(nonexec)
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "PREFLIGHT_PYTHON_EXECUTABLE_NOT_EXECUTABLE",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_nonabsolute_output_binding_fails(self):
        proc = self.run_precheck(
            output_path=pathlib.Path(
                "portable-admission.json"
            )
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "PREFLIGHT_PORTABLE_ADMISSION_OUTPUT_NOT_ABSOLUTE",
            proc.stderr,
        )

        self.assertFalse(
            self.sentinel.exists()
        )

    def test_portable_provider_nonzero_propagates_fail(self):
        proc = self.run_precheck(
            portable_mode="nonzero"
        )

        self.assertEqual(
            proc.returncode,
            17,
        )

        self.assertIn(
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=17",
            proc.stderr,
        )

        self.assertIn(
            "PORTABLE_RUNTIME_PROVIDER_FAILED",
            proc.stderr,
        )

    def test_portable_provider_nonpass_gate_propagates_fail(self):
        proc = self.run_precheck(
            portable_mode="nonpass"
        )

        self.assertNotEqual(
            proc.returncode,
            0,
        )

        self.assertIn(
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=FAIL",
            proc.stderr,
        )

        self.assertIn(
            "PORTABLE_RUNTIME_GATE_NOT_PASS",
            proc.stderr,
        )

    def test_all_required_providers_pass(self):
        proc = self.run_precheck()

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        self.assertTrue(
            self.output.is_file()
        )

        self.assertGreater(
            self.output.stat().st_size,
            0,
        )

        for marker in (
            "SCI_ORAN_PREFLIGHT_READY_GATE=PASS",
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0",
            "SCI_ORAN_PREFLIGHT_PORTABLE_EXIT_CODE=0",
            "SCI_ORAN_PREFLIGHT_PORTABLE_GATE=PASS",
            "SCI_ORAN_PREFLIGHT_PORTABLE_QUALIFICATION_GATE=PASS",
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=NONE",
        ):
            self.assertIn(
                marker,
                proc.stdout,
            )

    def test_portable_admission_path_provenance_present(self):
        proc = self.run_precheck()

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        marker = (
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_PATH="
            + str(self.output)
        )

        self.assertIn(
            marker,
            proc.stdout,
        )

    def test_existing_platform_markers_remain_compatible(self):
        proc = self.run_precheck()

        self.assertEqual(
            proc.returncode,
            0,
            proc.stderr,
        )

        for marker in (
            "SCI_ORAN_PREFLIGHT_READY_GATE=PASS",
            "SCI_ORAN_PREFLIGHT_DOCTOR_EXIT_CODE=0",
            "SCI_ORAN_PREFLIGHT_FAILURE_REASON=NONE",
        ):
            self.assertIn(
                marker,
                proc.stdout,
            )

    def test_runner_owns_explicit_named_bindings(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        required = (
            "--preflight-python-executable",
            "--preflight-require-jsonschema",
            "--preflight-portable-admission-output",
            "export SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE",
            "export SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA",
            "export SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT",
        )

        for value in required:
            self.assertIn(
                value,
                source,
            )

    def test_runner_rejects_ambient_binding_defaults(self):
        source = RUNNER.read_text(
            encoding="utf-8"
        )

        for name in (
            "SCI_ORAN_PREFLIGHT_PYTHON_EXECUTABLE",
            "SCI_ORAN_PREFLIGHT_REQUIRE_JSONSCHEMA",
            "SCI_ORAN_PREFLIGHT_PORTABLE_ADMISSION_OUTPUT",
        ):
            self.assertIn(
                "unset " + name,
                source,
            )

    def test_no_prompt12_specific_coupling(self):
        source = PREFLIGHT.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "prompt12",
            source.lower(),
        )

    def test_no_active_traffic_generation_command_added(self):
        source = PREFLIGHT.read_text(
            encoding="utf-8"
        )

        forbidden_patterns = (
            r"(?m)^\s*ping\s+",
            r"(?m)^\s*iperf3?\s+",
            r"sci-oran-user-plane-smoke\.sh",
        )

        for pattern in forbidden_patterns:
            self.assertIsNone(
                re.search(
                    pattern,
                    source,
                )
            )

    def test_no_package_bootstrap_path(self):
        source = PREFLIGHT.read_text(
            encoding="utf-8"
        )

        for value in (
            "pip install",
            "-m pip",
            "python -m venv",
            "virtualenv",
            "apt install",
            "apt-get install",
        ):
            self.assertNotIn(
                value,
                source,
            )

    def test_no_lifecycle_or_docker_mutation_added(self):
        source = PREFLIGHT.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "tb3-lifecycle.sh",
            source,
        )

        dangerous = re.compile(
            r"\bdocker\s+"
            r"(?:stop|restart|kill|rm|down)\b"
        )

        self.assertIsNone(
            dangerous.search(source)
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
