"""OFFLINE ONLY: isolated mock FIFO; never open real PRB or production paths."""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve()
BASE = HERE.parents[1]
INPUT = HERE.parent / 'postval-fixtures'
EXP='EXP-20261012-DL-18000K-R02'
RUN='RUN-20261012T081239Z-001'


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PostvalIntegration(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(prefix='postval-wiring-offline-')
        self.addCleanup(self.td.cleanup)
        t=Path(self.td.name)
        self.repo=t/'fake-repo'/'scripts'/'experiment-harness'
        self.repo.mkdir(parents=True)
        for name in ('prompt12-t2-postval-fast-trigger.py', 'prompt12-t2-postval-tail-reader.py'):
            shutil.copy2(BASE/name, self.repo/name)
        self.parser=self.repo/'parser.py'
        shutil.copy2(INPUT/'parser.py',self.parser)
        self.mod=import_file('postval_isolated_gate',self.repo/'prompt12-t2-postval-fast-trigger.py')
        self.run=t/'evidence'/'t2-26to39'/EXP/RUN
        for sub in ('control','runtime','runtime/ratio-bindings','raw','processed'):
            (self.run/sub).mkdir(parents=True,exist_ok=True)
        self.raw=self.run/'raw'/'iperf3-receiver.stdout.log'
        self.stamps=self.run/'raw'/'iperf3-receiver.timestamps.jsonl'
        shutil.copy2(INPUT/'receiver-90s.log',self.raw)
        shutil.copy2(INPUT/'timestamps-90s.jsonl',self.stamps)
        self.canonical=json.loads((INPUT/'canonical-90s.jsonl').read_text().splitlines()[-1])
        self.latest=self.canonical['timestamp_utc_ns']
        self.fifo=t/'mock-test-only.fifo'
        os.mkfifo(self.fifo)
        self.rfd=os.open(self.fifo, os.O_RDONLY|os.O_NONBLOCK)
        self.addCleanup(os.close,self.rfd)
        self.ratio=self.run/'runtime'/'ratio-bindings'/'T2.binding.json'
        self.ratio.write_text(json.dumps({
            'schema':'sci_oran_prompt12_v2_pretrigger_ratio_binding_v1',
            'experiment_id':EXP,'run_id':RUN,'transition_label':'T2',
            'transition_index':2,'requested_ratio_pct':75}))
        self.out=self.run/'control'/'T2.executor.json'
        self.plan=self.run/'runtime'/'resumed-single-transition.json'
        # Production materializer's exact option semantics, no real network.
        self.trigger=['python3','/nonexistent/prompt12-precontrol-trigger-executor.py',
                      '--precontrol-json',str(self.run/'precontrol'/'T2.json'),
                      '--mode','fifo','--max-age-ms','800','--output',str(self.out),
                      '--fifo-path',str(self.fifo),'--trigger-token','TRIGGER',
                      '--control-authorization-token','@PROMPT12_CONTROL_AUTHORIZATION_TOKEN@']
        self.materialization={
            'schema':self.mod.PLAN_SCHEMA, 'transition_label':'T2','transition_index':2,
            'executed_transition_ordinal':1,'expected_timeline_event_count':3,
            'expected_actuator_transaction_count':1,
            'synthetic_prior_transition_events':False,'skipped_transition_bindings_consumed':False,
            't3_handoff_present':False,'t3_trigger_present':False,'command_executed':False,
            'control_executed':False,'traffic_executed':False,
            'ratio_bind_command':['python3','/fake/ratio-writer.py','--transition-label','T2',
                                  '--transition-index','2','--requested-ratio-pct','75',
                                  '--output',str(self.ratio)],
            'trigger_command':self.trigger,
            'traffic_command':['python3','/fake/traffic.py','--dummy','value',str(self.raw),str(self.stamps),'fixed'],
        }
        self.plan.write_text(json.dumps(self.materialization))
        (self.run/'runtime'/'runtime-profile.json').write_text(json.dumps({
            'schema':self.mod.PROFILE_SCHEMA,'run_directory':str(self.run),
            'experiment_id':EXP,'run_id':RUN,'max_age_ms':800,'traffic_duration_s':180,
            'actuator_fifo_path':str(self.fifo),'trigger_token':'TRIGGER',
            'tool_paths':{'parser':str(self.parser)},
        }))

    def info(self):
        return self.mod.load_binding(self.plan)

    def status(self, ms=350, op='postval-R02-single-attempt-test'):
        with patch.object(self.mod.time,'time_ns',return_value=self.latest+ms*1_000_000):
            return self.mod.live(self.info(),op)

    def test_real_R02_tail_one_trigger_only(self):
        value=self.status()
        self.assertEqual(value['GATE'],'PASS_PENDING_READBACK_AND_POSTVAL')
        self.assertEqual(value['sample']['latest_interval_end_s'],90.0)
        self.assertEqual(os.read(self.rfd,100),b'TRIGGER\n')
        self.assertEqual(json.loads((self.run/'control'/'T2.postval.outcome.json').read_text())['GATE'],
                         'PASS_PENDING_READBACK_AND_POSTVAL')
        self.assertTrue((self.run/'control'/'T2.trigger-intent.json').exists())
        self.assertTrue((self.run.parent.parent/'.t2-operation-claims'/'postval-R02-single-attempt-test.json').exists())

    def test_repeat_same_run_denied(self):
        self.status(); os.read(self.rfd,100)
        with self.assertRaisesRegex(self.mod.PostvalError,'RUN_ALREADY_CONSUMED'):
            self.status(op='postval-R02-different-identifier')
        self.assertEqual(os.read(self.rfd,100),b'')

    def test_800_ms_freshness(self):
        value=self.status(ms=800)
        self.assertEqual(value['AGE_AT_FIFO_WRITE_NS'],800_000_000)
        self.assertEqual(os.read(self.rfd,100),b'TRIGGER\n')

    def test_801_ms_expiry_no_trigger_and_no_replay(self):
        with self.assertRaisesRegex(self.mod.PostvalError,'FRESHNESS_OVER_800_MS_AT_WRITE'):
            # Avoid 90s wait by injecting tail reader status directly.
            with patch.object(self.mod,'source_at_90',return_value={
                'latest_sample_timestamp_utc_ns':self.latest,
                'latest_interval_end_s':90.0,'GATE':'PASS'}):
                with patch.object(self.mod.time,'time_ns',return_value=self.latest+801_000_000):
                    self.mod.live(self.info(),'postval-R02-expired-clock-test')
        self.assertEqual(os.read(self.rfd,100),b'')
        self.assertTrue((self.run/'control'/'T2.trigger-intent.json').exists())

    def test_control_authorization_requires_two_interlocks(self):
        env1=os.environ.pop('SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE',None)
        env2=os.environ.pop('SCI_ORAN_T2_POSTVAL_V1_ENABLE',None)
        try:
            result=self.mod.main(['--mode','live','--materialization',str(self.plan),
                                  '--live-authorization-token',self.mod.LIVE_TOKEN,
                                  '--control-authorization-token',self.mod.CONTROL_TOKEN])
            self.assertEqual(result,70)
            self.assertFalse((self.run/'control'/'T2.trigger-intent.json').exists())
        finally:
            if env1 is not None:os.environ['SCI_ORAN_PROMPT12_LIVE_CONTROL_ENABLE']=env1
            if env2 is not None:os.environ['SCI_ORAN_T2_POSTVAL_V1_ENABLE']=env2

    def test_missing_fifo_reader_blocks_and_consumes_attempt(self):
        os.close(self.rfd)
        self.rfd=os.open(self.fifo, os.O_RDONLY|os.O_NONBLOCK)
        # Close again; keep an unrelated safe reader registered at cleanup.
        os.close(self.rfd)
        self.rfd=os.open(os.devnull, os.O_RDONLY)
        with self.assertRaises(OSError):
            self.status(op='postval-R02-no-reader-attempt')
        self.assertTrue((self.run/'control'/'T2.trigger-intent.json').exists())
        self.assertIn('failure_reason',json.loads((self.run/'control'/'T2.postval.outcome.json').read_text()))

    def test_existing_legacy_intent_blocks_without_fifo(self):
        (self.run/'control'/'T2.trigger-intent.json').write_text('{}')
        with self.assertRaisesRegex(self.mod.PostvalError,'RUN_ALREADY_CONSUMED'):
            self.status()
        self.assertEqual(os.read(self.rfd,100),b'')

    def test_identity_conflicting_ratio_is_rejected(self):
        binding=json.loads(self.ratio.read_text()); binding['requested_ratio_pct']=50
        self.ratio.write_text(json.dumps(binding))
        with self.assertRaisesRegex(self.mod.PostvalError,'RATIO_BINDING_NOT_PROVEN'):
            self.status()
        self.assertFalse((self.run/'control'/'T2.trigger-intent.json').exists())

    def test_corrupted_R02_raw_blocks_fifo(self):
        raw=bytearray(self.raw.read_bytes()); raw[-12]^=1; self.raw.write_bytes(raw)
        with patch.object(self.mod.time,'time_ns',return_value=self.latest+350_000_000):
            with self.assertRaises(self.mod.PostvalError):
                self.mod.live(self.info(),'postval-R02-corrupt-raw-test')
        self.assertEqual(os.read(self.rfd,100),b'')
        self.assertTrue((self.run/'control'/'T2.trigger-intent.json').exists())

    def test_inspect_has_no_side_effects(self):
        self.assertEqual(self.mod.main(['--materialization',str(self.plan),'--mode','inspect']),0)
        self.assertFalse((self.run/'control'/'T2.trigger-intent.json').exists())


if __name__=='__main__':
    unittest.main()
