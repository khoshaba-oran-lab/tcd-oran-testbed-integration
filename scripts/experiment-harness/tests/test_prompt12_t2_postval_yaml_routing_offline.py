"""Static fail-closed Ansible routing contract; no Ansible invoked."""
import unittest
from pathlib import Path
import yaml

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PLAY=REPO/'sci-oran'/'ansible'/'experiments'/'prompt12'/'playbooks'


class OfflinePlaybookContract(unittest.TestCase):
    def setUp(self):
        self.resume=yaml.safe_load((PLAY/'prompt12-resume-single-transition.yml').read_text())[0]
        self.parent=yaml.safe_load((PLAY/'prompt12-t2-experiment.yml').read_text())

    def get_task(self,needle):
        matches=[]
        for task in self.resume['tasks']:
            if 'block' in task:
                matches += [x for x in task['block'] if needle in x.get('name','')]
        self.assertEqual(len(matches),1,needle)
        return matches[0]

    def test_legacy_critical_kept_but_only_legacy(self):
        critical=self.get_task('Execute resumed T2 initial precontrol')
        self.assertIn('legacy',critical['when'])
        self.assertIn('prompt12-t2-critical-section.py', ' '.join(critical['ansible.builtin.command']['argv']))

    def test_postval_requires_specific_protocol(self):
        task=self.get_task('Execute POSTVAL one-shot')
        self.assertIn('postval-v1',task['when'])
        self.assertIn('SCI_ORAN_T2_POSTVAL_V1_ENABLE',task['environment'])
        self.assertIn('prompt12-t2-postval-fast-trigger.py', ' '.join(task['ansible.builtin.command']['argv']))

    def test_prepared_ratio_happens_before_scientific_traffic(self):
        tasks=self.resume['tasks']
        names=[t.get('name','') for t in tasks]
        self.assertLess(names.index('Pre-bind static ratio before scientific traffic for POSTVAL'),
                        names.index('Run one bounded T2 experiment with evidence-preserving failure handling'))
        self.assertIn('postval-v1', tasks[names.index('Pre-bind static ratio before scientific traffic for POSTVAL')]['when'])

    def test_pre_post_stationarity_not_faked(self):
        tasks=self.get_task('Execute pure resumed T2 post-step stationarity')
        self.assertIn('legacy',tasks['when'])
        post=self.get_task('Require T2 post-step stationarity')
        self.assertIn('legacy',post['when'])
        self.assertIn('postval-v1', (PLAY/'prompt12-t2-experiment.yml').read_text())
        self.assertIn('prompt12-t2-postval-evidence-adjudicator.py', (PLAY/'prompt12-t2-experiment.yml').read_text())

    def test_parent_authentication_uses_distinct_postval_token(self):
        first=self.parent[0]['tasks'][0]
        condition=' '.join(str(x) for x in first['ansible.builtin.assert']['that'])
        self.assertIn('AUTHORISE_ONE_PROMPT12_T2_POSTVAL_MACRO',condition)
        self.assertIn('AUTHORISE_ONE_PROMPT12_T2_MACRO',condition)


if __name__=='__main__':unittest.main()
