import importlib.util
import io
import json
import os
import pathlib
from unittest.mock import patch
import sys
import tempfile
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name('prestart_guard.py')
spec = importlib.util.spec_from_file_location('prestart_guard', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class GuardTests(unittest.TestCase):
    def test_materializer_failure_exposes_exact_reason(self):
        class Result:
            returncode = 65
            stdout = ''
            stderr = 'PROMPT12_RUNTIME_PROFILE_MATERIALIZER_GATE=FAIL\nFAIL_REASON=EXPERIMENT_ID_INVALID\n'
        with patch.object(mod.subprocess,'run',return_value=Result()):
            with self.assertRaises(mod.GateFailure) as raised:
                mod.run(['python3', '-B', 'tool.py'], 'PROFILE_DRY_RUN')
        self.assertEqual(raised.exception.reason, 'PROFILE_DRY_RUN_REJECTED')
        self.assertIn('EXPERIMENT_ID_INVALID', raised.exception.detail)

    def test_ratio_paths_reject_external_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            sandbox=root/'scratch'; sandbox.mkdir()
            run_dir=sandbox/'EXP'/'RUN'
            outside=root/'real-evidence'/'ratio-bindings'
            paths=[str(outside / f'T{i}.json') for i in range(6)]
            with self.assertRaises(mod.GateFailure) as raised:
                mod.validate_sandbox_ratio_paths(paths, sandbox, run_dir)
            self.assertEqual(raised.exception.reason,'RATIO_BINDING_PATH_OUTSIDE_SANDBOX')

    def test_ratio_paths_reject_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            sandbox=root/'scratch'; sandbox.mkdir()
            run_dir=sandbox/'EXP'/'RUN'
            runtime=run_dir/'runtime'; runtime.mkdir(parents=True)
            outside=root/'outside'; outside.mkdir()
            (runtime/'ratio-bindings').symlink_to(outside, target_is_directory=True)
            paths=[str(runtime/'ratio-bindings'/f'T{i}.json') for i in range(6)]
            with self.assertRaises(mod.GateFailure) as raised:
                mod.validate_sandbox_ratio_paths(paths, sandbox, run_dir)
            self.assertEqual(raised.exception.reason,'SANDBOX_ROOT_INVALID')

    def test_ratio_paths_reject_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            sandbox=root/'scratch'; sandbox.mkdir()
            run_dir=sandbox/'EXP'/'RUN'
            binding=run_dir/'runtime'/'ratio-bindings'/'T1.json'
            with self.assertRaises(mod.GateFailure) as raised:
                mod.validate_sandbox_ratio_paths([str(binding)]*6, sandbox, run_dir)
            self.assertEqual(raised.exception.reason,'RATIO_BINDING_PATH_DUPLICATE')

    def test_contract_correct_gate_does_not_execute_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=pathlib.Path(tmp)
            repo=t/'repo'
            repo.mkdir()
            evidence=t/'real-evidence'; evidence.mkdir()
            scripts=repo/'scripts'/'experiment-harness'; scripts.mkdir(parents=True)
            for name in ('prompt12-bounded-runtime-profile-materializer.py','prompt12-bounded-production-binding-builder.py','prompt12-resume-precontrol-materializer.py','prompt12-resume-single-transition-materializer.py','prompt12-production-provider-launch-materializer.py','prompt12-production-provider-identity-materializer.py'):
                (scripts/name).write_text('#stub\n')
            frozen=t/'frozen.json'; frozen.write_text('{}')
            portable=t/'portable.json'; portable.write_text('{}')
            root=pathlib.Path('/home/khoshaba/sci-oran/prompt12-runtime-aabbcc'); fifo=root/'actuator.fifo'
            inputs=['--repo',str(repo),'--approved-head','abc','--evidence-root',str(evidence),'--experiment-id','EXP-VALID','--run-id','RUN-VALID','--portable-admission',str(portable),'--frozen-config',str(frozen)]
            def fake_run(argv,label,timeout=40):
                if label=='GIT_HEAD': return 'abc'
                if label=='GIT_BRANCH': return 'main'
                if label=='GIT_STATUS': return ''
                if label in ('DOCKER_INSPECT','DOCKER_ALL_CONTAINERS'): return ''
                if label=='PROVIDER_IDENTITY_DRY_RUN': return json.dumps({'provider_identity':'prompt12-provider-aabbcc'})
                if label=='PROFILE_DRY_RUN':
                    idx=argv.index('--evidence-root')
                    sandbox=pathlib.Path(argv[idx+1])
                    rt=sandbox/'EXP-VALID'/'RUN-VALID'/'runtime'; rt.mkdir(parents=True)
                    (rt/'allocation.json').write_text('{}')
                    profile={'experiment_id':'EXP-VALID','run_id':'RUN-VALID','actuator_fifo_path':str(fifo),'traffic_duration_s':180,'max_age_ms':800,'ratio_binding_paths':[str(rt/'ratio-bindings'/f'T{i}.binding.json') for i in range(1,7)]}
                    (rt/'runtime-profile.json').write_text(json.dumps(profile))
                    return '{}'
                if label=='BINDINGS_DRY_RUN': pathlib.Path(argv[argv.index('--output')+1]).write_text('{}');return '{}'
                if label=='RESUME_DRY_RUN': pathlib.Path(argv[argv.index('--output')+1]).write_text('{}');return '{}'
                if label=='T2_DRY_RUN': pathlib.Path(argv[argv.index('--output')+1]).write_text(json.dumps({'first_scientific_transition':'T2','command_executed':False,'control_executed':False,'traffic_executed':False,'t3_handoff_present':False,'t3_trigger_present':False}));return '{}'
                if label=='PROVIDER_LAUNCH_DRY_RUN':return json.dumps(['/usr/bin/python3','tool'])
                raise AssertionError(label)
            original_is_dir = pathlib.Path.is_dir
            def mock_is_dir(path):
                if str(path) == '/home/khoshaba/sci-oran':
                    return True
                return original_is_dir(path)
            with patch.object(sys,'argv',['prestart_guard.py']+inputs), patch.object(mod.socket,'gethostname',return_value='tb3-dell'), patch.object(mod.shutil,'which',return_value='/usr/bin/docker'), patch.object(mod,'run',side_effect=fake_run) as spy, patch.object(pathlib.Path,'is_dir',mock_is_dir):
                result=mod.main()
            self.assertEqual(result['PRESTART_GATE'],'PASS')
            self.assertEqual(result['ACTUAL_EVIDENCE_WRITE_REQUESTED'],'NO')
            self.assertFalse(root.exists())
            self.assertFalse((evidence/'EXP-VALID').exists())
            self.assertEqual(spy.call_count,11)

if __name__=='__main__': unittest.main()
