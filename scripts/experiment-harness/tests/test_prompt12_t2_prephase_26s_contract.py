#!/usr/bin/env python3

import pathlib
import re
import unittest


REPO = pathlib.Path(
    "/home/khoshaba/project/tcd-oran-testbed-integration"
)

PLAYBOOK = (
    REPO
    / "sci-oran"
    / "ansible"
    / "experiments"
    / "prompt12"
    / "playbooks"
    / "prompt12-resume-single-transition.yml"
)


class Prompt12T2Prephase26sContractTest(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(
            encoding="utf-8"
        )

    def prephase_block(self):
        marker = (
            "- name: Accumulate minimum "
            "Prompt12 pre-phase"
        )

        self.assertEqual(
            self.text.count(marker),
            1,
        )

        start = self.text.index(marker)

        end = self.text.find(
            "\n    - name:",
            start + len(marker),
        )

        self.assertNotEqual(
            end,
            -1,
        )

        return self.text[start:end]

    def test_prephase_is_exactly_26_seconds(self):
        block = self.prephase_block()

        values = re.findall(
            r"(?m)^\s+seconds:\s*([0-9]+)\s*$",
            block,
        )

        self.assertEqual(
            values,
            ["26"],
        )

    def test_old_11_second_value_is_absent_from_prephase(self):
        block = self.prephase_block()

        self.assertNotRegex(
            block,
            r"(?m)^\s+seconds:\s*11\s*$",
        )

    def test_prephase_remains_before_initial_precontrol(self):
        pause = self.text.index(
            "Accumulate minimum Prompt12 pre-phase"
        )

        precontrol = self.text.index(
            "Execute resumed T2 initial precontrol"
        )

        self.assertLess(
            pause,
            precontrol,
        )

    def test_prephase_still_requires_active_traffic_after_wait(self):
        pause = self.text.index(
            "Accumulate minimum Prompt12 pre-phase"
        )

        active = self.text.index(
            "Require bounded traffic active "
            "after minimum pre-phase"
        )

        precontrol = self.text.index(
            "Execute resumed T2 initial precontrol"
        )

        self.assertLess(
            pause,
            active,
        )

        self.assertLess(
            active,
            precontrol,
        )

    def test_prephase_still_requires_evidence_growth_before_precontrol(self):
        growth = self.text.index(
            "Require bounded traffic evidence growth"
        )

        precontrol = self.text.index(
            "Execute resumed T2 initial precontrol"
        )

        self.assertLess(
            growth,
            precontrol,
        )

    def test_stationarity_thresholds_not_encoded_in_wait_repair(self):
        block = self.prephase_block()

        self.assertNotIn(
            "cv_max_pct",
            block,
        )

        self.assertNotIn(
            "mean_shift_max_pct",
            block,
        )

    def test_exactly_once_trigger_remains_after_initial_precontrol(self):
        precontrol = self.text.index(
            "Execute resumed T2 initial precontrol"
        )

        trigger = self.text.index(
            "Execute exactly-once T2 scientific trigger"
        )

        self.assertLess(
            precontrol,
            trigger,
        )


if __name__ == "__main__":
    unittest.main()
