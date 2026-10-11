#!/usr/bin/env python3
"""Controller macro guard with mocked ansible process; no live remote call."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'scripts/experiment-harness/prompt12-t2-experiment.py'
sp = importlib.util.spec_from_file_location('macro_controller', SRC)
M = importlib.util.module_from_spec(sp)
sp.loader.exec_module(M)
EXP='EXP-20261011-DL-18000K-R01'
RUN='RUN-20261011T121212Z-001'


class FakePopen:
    def __init__(self, argv, cwd=None, stdin=None, stdout=None, stderr=None,
                 text=None, bufsize=None, response=None, rc=0):
        self.argv=argv
        self.stdout=iter(response or ['SCI_ORAN_EXPERIMENT_GATE=PASS\n',
                                      'SCIENTIFIC_T2_GATE=PASS\n'])
        self.rc=rc
    def wait(self):
        return self.rc


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.claims=Path(self.tmp.name) / 'claims'
        self.args=SimpleNamespace(mode='offline-qualify',repo=REPO,
            approved_head=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],
                                                  text=True).strip(),
            experiment_id=EXP,run_id=RUN,target='tb3-dell',
            confirm=False,authorization_token=None)

    def test_offline_identity_checks_and_no_execution(self):
        self.assertTrue(M.validate(self.args).is_file())
        with patch.object(M, 'offline', return_value=0) as offline, patch.object(M,'live') as live:
            p=M.main(['--mode','offline-qualify','--repo',str(REPO),
                      '--approved-head',self.args.approved_head,
                      '--experiment-id',EXP,'--run-id',RUN,'--target','tb3-dell'])
            self.assertEqual(p,0)
            offline.assert_called_once()
            live.assert_not_called()

    def test_offline_rejects_live_authorization(self):
        self.args.confirm=True
        with self.assertRaisesRegex(M.ExperimentError,'OFFLINE_REJECTS'):
            M.validate(self.args)

    def test_invalid_id_rejected_before_any_remote_action(self):
        self.args.run_id='../escape'
        with self.assertRaisesRegex(M.ExperimentError,'SCIENTIFIC_ID_FORMAT_INVALID'):
            M.validate(self.args)

    def test_mismatched_run_dates_rejected(self):
        self.args.run_id='RUN-20261012T120000Z-001'
        with self.assertRaisesRegex(M.ExperimentError,'SCIENTIFIC_ID_DATE_MISMATCH'):
            M.validate(self.args)

    def test_wrong_head_rejected(self):
        self.args.approved_head='0'*40
        with self.assertRaisesRegex(M.ExperimentError,'GIT_HEAD_NOT_APPROVED'):
            M.validate(self.args)

    def test_live_refused_without_canonical_repo_and_host(self):
        # Test both guards explicitly. Running this test on coll.vntu.org is valid.
        self.args.mode='live';self.args.confirm=True
        self.args.authorization_token=M.MACRO_TOKEN
        with patch.object(M, 'REPO', self.args.repo.parent):
            with self.assertRaisesRegex(M.ExperimentError, 'LIVE_REPOSITORY_NOT_CANONICAL'):
                M.validate(self.args)
        with patch.object(M, 'REPO', self.args.repo), \
             patch.object(M.socket, 'gethostname', return_value='not-controller'), \
             patch.object(M.socket, 'getfqdn', return_value='not-controller.invalid'):
            with self.assertRaisesRegex(M.ExperimentError, 'LIVE_CONTROLLER_HOST_INVALID'):
                M.validate(self.args)

    def test_live_requires_explicit_authorization_on_canonical_host(self):
        # Confirm fail-closed behavior regardless of the test machine's hostname.
        self.args.mode='live';self.args.confirm=True
        self.args.authorization_token=M.MACRO_TOKEN
        with patch.object(M, 'REPO', self.args.repo), \
             patch.object(M.socket, 'gethostname', return_value='coll'), \
             patch.dict(M.os.environ, {M.LIVE_ENV: 'NO'}):
            with self.assertRaisesRegex(M.ExperimentError, 'LIVE_MACRO_AUTHORIZATION_MISSING'):
                M.validate(self.args)

    def test_controller_claim_survives_success_and_forbids_replay(self):
        with patch.object(M,'CLAIM_ROOT',self.claims),patch.object(M.subprocess,'Popen',side_effect=FakePopen) as popen:
            self.assertEqual(M.live(self.args,Path('/tmp/no-real-playbook.yml')),0)
            record=self.claims/EXP/RUN/'outcome.json'
            self.assertEqual(json.loads(record.read_text())['scientific_t2_gate'],'PASS')
            with self.assertRaisesRegex(M.ExperimentError,'ALREADY_CONSUMED_NO_REPLAY'):
                M.live(self.args,Path('/tmp/no-real-playbook.yml'))
            popen.assert_called_once()

    def test_run_id_never_reused_across_experiment_ids(self):
        with patch.object(M,'CLAIM_ROOT',self.claims),patch.object(M.subprocess,'Popen',side_effect=FakePopen) as popen:
            self.assertEqual(M.live(self.args,Path('/tmp/mock-playbook.yml')),0)
            self.args.experiment_id = 'EXP-20261011-DL-18000K-R02'
            with self.assertRaisesRegex(M.ExperimentError,'RUN_ID_ALREADY_CONSUMED_NO_REPLAY'):
                M.live(self.args,Path('/tmp/mock-playbook.yml'))
            popen.assert_called_once()

    def test_installed_inventory_respects_controller_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv = Path(tmp)/'inventory.ini'
            inv.write_text('[sci_oran_vms]\ntb3-dell ansible_host=127.0.0.1\n')
            with patch.dict(M.os.environ, {'SCI_ORAN_INVENTORY':str(inv)}):
                self.assertEqual(M.installed_inventory(REPO), inv)

    def test_rc_zero_without_two_pass_markers_still_blocks_and_consumes(self):
        def fake(*a,**kw):
            return FakePopen(*a,**kw,response=['TASK FINISHED\n'],rc=0)
        with patch.object(M,'CLAIM_ROOT',self.claims),patch.object(M.subprocess,'Popen',side_effect=fake):
            self.assertEqual(M.live(self.args,Path('/tmp/mock-playbook.yml')),70)
            failure=json.loads((self.claims/EXP/RUN/'failure.json').read_text())
            self.assertFalse(failure['scientific_pass'])
            self.assertIn('UNKNOWN',failure['live_state'])
            self.assertFalse((self.claims/EXP/RUN/'outcome.json').exists())

    def test_unexpected_ansible_exception_preserves_claim(self):
        with patch.object(M,'CLAIM_ROOT',self.claims),patch.object(M.subprocess,'Popen',side_effect=OSError('failed')):
            self.assertEqual(M.live(self.args,Path('/tmp/mock-playbook.yml')),70)
            self.assertTrue((self.claims/EXP/RUN/'intent.json').exists())
            self.assertTrue((self.claims/EXP/RUN/'failure.json').exists())

    def test_no_implicit_lifecycle_or_shell_execution(self):
        source=SRC.read_text()
        self.assertNotIn('tb3-lifecycle.sh',source)
        self.assertNotIn('shell=True',source)
        self.assertIn('--limit',source)
        self.assertIn('SCIENTIFIC_T2_GATE=PASS',source)


if __name__=='__main__':
    unittest.main()
