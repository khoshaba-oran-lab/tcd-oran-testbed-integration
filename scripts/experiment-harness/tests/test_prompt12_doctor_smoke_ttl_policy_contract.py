#!/usr/bin/env python3
"""Offline proof that both Doctor age gates consume the same policy TTL.

Never launches Docker, smoke, Doctor, readiness probes or scientific traffic.
The original readiness-artifact Bash block is executed with synthetic input.
"""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / 'deploy/phase-2-flexric/tb3-runtime/locks/user-plane-readiness.policy'
DOCTOR = ROOT / 'scripts/sci-oran-doctor.sh'


def policy_ttl():
    matches = [line.split('=', 1)[1].strip() for line in POLICY.read_text().splitlines()
               if line.startswith('SMOKE_EVIDENCE_MAX_AGE_SECONDS=')]
    if len(matches) != 1:
        raise ValueError('Policy TTL missing or duplicated')
    return int(matches[0])


def artifact_readiness_section():
    source = DOCTOR.read_text(encoding='utf-8')
    start = 'echo "===== READINESS FRESHNESS ====="'
    end = 'echo "===== FINAL READY DECISION ====="'
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError('Cannot uniquely locate real Doctor freshness section')
    return source.split(start, 1)[1].split(end, 1)[0]


def evaluate_actual_bash(age_seconds, max_age, stored_age=None):
    """Run unmodified production bash excerpt against a synthetic artifact."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    fmt = lambda date: date.strftime('%Y-%m-%dT%H:%M:%SZ')
    with tempfile.TemporaryDirectory(prefix='sci-oran-ttl-offline-') as temp:
        artifact = Path(temp) / 'readiness.env'
        artifact.write_text(
            'READINESS_ID=RDY-TEST\n'
            f'GENERATED_AT_UTC={fmt(now)}\n'
            f'USER_PLANE_EVIDENCE_TIMESTAMP={fmt(now - timedelta(seconds=age_seconds))}\n'
            f'USER_PLANE_EVIDENCE_AGE_SECONDS={age_seconds if stored_age is None else stored_age}\n',
            encoding='utf-8',
        )
        env = dict(os.environ)
        env.update({
            'READINESS_ID': 'RDY-TEST',
            'UTC_TIMESTAMP': fmt(now - timedelta(seconds=10)),
            'READINESS_ARTIFACT_RUN_PATH': str(artifact),
            'PROCESS_CONTINUITY_GATE': 'PASS',
            'READINESS_ARTIFACT_GATE': 'PASS',
            'USER_PLANE_MAX_AGE_SECONDS': str(max_age),
        })
        script = 'set -Eeuo pipefail\n' + artifact_readiness_section()
        result = subprocess.run(['bash', '-c', script], env=env, text=True,
                                capture_output=True, timeout=10, check=False)
        if result.returncode:
            raise AssertionError(f'Bash readiness section failed: {result.stderr}')
        values = dict(line.split('=', 1) for line in result.stdout.splitlines()
                      if '=' in line and line.split('=', 1)[0].isidentifier())
        return values


class SmokeTtlContractTests(unittest.TestCase):
    def test_diagnostic_ttl_is_1800_seconds(self):
        self.assertEqual(policy_ttl(), 1800)

    def test_doctor_reads_policy_in_first_age_check(self):
        source = DOCTOR.read_text(encoding='utf-8')
        self.assertIn('SMOKE_EVIDENCE_MAX_AGE_SECONDS', source)
        self.assertIn('USER_PLANE_MAX_AGE_SECONDS', source)
        self.assertNotIn('USER_PLANE_MAX_AGE_AT_ARTIFACT_SECONDS="300"', source)
        self.assertIn('USER_PLANE_MAX_AGE_AT_ARTIFACT_SECONDS="${USER_PLANE_MAX_AGE_SECONDS:-}"', source)

    def test_artifact_gate_passes_at_400_seconds_under_policy(self):
        gates = evaluate_actual_bash(400, policy_ttl())
        self.assertEqual(gates['READINESS_USER_PLANE_MAX_AGE_SECONDS'], '1800')
        self.assertEqual(gates['READINESS_FRESHNESS_USER_PLANE_AGE_GATE'], 'PASS')
        self.assertEqual(gates['READINESS_FRESHNESS_GATE'], 'PASS')

    def test_artifact_gate_respects_runtime_threshold_not_hardcoded(self):
        gates = evaluate_actual_bash(400, 300)
        self.assertEqual(gates['READINESS_FRESHNESS_USER_PLANE_AGE_GATE'], 'FAIL')
        self.assertEqual(gates['READINESS_FRESHNESS_GATE'], 'FAIL')

    def test_artifact_gate_fails_beyond_extended_ttl(self):
        gates = evaluate_actual_bash(1900, policy_ttl())
        self.assertEqual(gates['READINESS_FRESHNESS_USER_PLANE_AGE_GATE'], 'FAIL')
        self.assertEqual(gates['READINESS_FRESHNESS_GATE'], 'FAIL')

    def test_artifact_gate_fails_closed_if_policy_invalid(self):
        gates = evaluate_actual_bash(400, '')
        self.assertEqual(gates['READINESS_USER_PLANE_MAX_AGE_SECONDS'], 'MISSING')
        self.assertEqual(gates['READINESS_FRESHNESS_USER_PLANE_AGE_GATE'], 'FAIL')
        self.assertEqual(gates['READINESS_FRESHNESS_GATE'], 'FAIL')

    def test_timestamp_drift_still_blocks(self):
        gates = evaluate_actual_bash(400, policy_ttl(), stored_age=100)
        self.assertEqual(gates['READINESS_FRESHNESS_USER_PLANE_AGE_COHERENCE_GATE'], 'FAIL')
        self.assertEqual(gates['READINESS_FRESHNESS_GATE'], 'FAIL')

    def test_doctor_bash_syntax_and_no_smoke_modification(self):
        result = subprocess.run(['bash', '-n', str(DOCTOR)], capture_output=True,
                                text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((ROOT / 'scripts/sci-oran-user-plane-smoke.sh').is_file())


if __name__ == '__main__':
    unittest.main()
