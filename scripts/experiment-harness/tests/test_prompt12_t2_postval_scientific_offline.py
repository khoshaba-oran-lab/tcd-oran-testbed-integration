"""Offline statistical and safety regression for explicit POSTVAL protocol."""
import importlib.util
import json
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FIX=HERE/'postval-fixtures'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

VAL=module('postval_validator',BASE/'prompt12-t2-postval-evidence-adjudicator.py')
EV=VAL.evaluator()


class PostvalScience(unittest.TestCase):
    def setUp(self):
        self.rows=[json.loads(l) for l in (FIX/'canonical-90s.jsonl').read_text().splitlines() if l.strip()]

    def test_real_R02_frozen_pre_window_stationary(self):
        metrics=VAL.frozen_stationarity(self.rows,'80.0','90.0',EV)
        self.assertEqual(metrics['span_s'],'80.0-90.0')
        self.assertEqual(metrics['record_first'],'IPERF-RX-LINE-000000406')
        self.assertEqual(metrics['record_last'],'IPERF-RX-LINE-000000455')

    def test_real_R02_selected_90s_raw_provenance(self):
        origin={'last_sequence':455,
                'latest_sample_timestamp_utc_ns':self.rows[-1]['timestamp_utc_ns'],
                'raw_line_sha256':self.rows[-1]['raw_line_sha256'] if 'raw_line_sha256' in self.rows[-1] else None}
        # The canonical interval schema need not carry line SHA; provenance is
        # instead read from the immutable historical timestamp capture.
        stamps=[json.loads(l) for l in (FIX/'timestamps-90s.jsonl').read_text().splitlines()]
        row=stamps[-1]
        origin={'last_sequence':row['sequence'],
                'latest_sample_timestamp_utc_ns':row['rx_wall_ns'],
                'raw_line_sha256':row['raw_line_sha256']}
        got=VAL.verify_trigger_raw(origin,FIX/'receiver-90s.log',FIX/'timestamps-90s.jsonl')
        self.assertEqual(got['raw_line_sha256'],row['raw_line_sha256'])

    def test_tampered_timestamp_or_sha_rejected(self):
        row=json.loads((FIX/'timestamps-90s.jsonl').read_text().splitlines()[-1])
        fake={'last_sequence':row['sequence'], 'latest_sample_timestamp_utc_ns':row['rx_wall_ns'],
              'raw_line_sha256':'0'*64}
        with self.assertRaisesRegex(VAL.EvidenceError,'PROVENANCE_INVALID'):
            VAL.verify_trigger_raw(fake,FIX/'receiver-90s.log',FIX/'timestamps-90s.jsonl')

    def test_missing_pre_sample_rejected_not_fabricated(self):
        altered=[r for r in self.rows if r.get('interval_start_s')!=85.0]
        with self.assertRaisesRegex(VAL.EvidenceError,'FROZEN_WINDOW_COUNT_INVALID'):
            VAL.frozen_stationarity(altered,'80.0','90.0',EV)

    def test_nonstationary_prewindow_fails(self):
        altered=[dict(r) for r in self.rows]
        for r in altered:
            if r.get('interval_start_s') == 85.0:
                r['throughput_kbit_s']=10
        with self.assertRaisesRegex(VAL.EvidenceError,'FROZEN_WINDOW_STATIONARITY_FAILED'):
            VAL.frozen_stationarity(altered,'80.0','90.0',EV)

    def test_frozen_postwindow_is_not_invented_from_pre(self):
        with self.assertRaisesRegex(VAL.EvidenceError,'FROZEN_WINDOW_COUNT_INVALID'):
            VAL.frozen_stationarity(self.rows,'120.0','130.0',EV)


if __name__=='__main__': unittest.main()
