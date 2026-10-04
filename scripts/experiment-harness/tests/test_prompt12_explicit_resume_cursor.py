#!/usr/bin/env python3

import ast
import importlib.util
import json
import pathlib
import unittest


HARNESS = pathlib.Path(__file__).resolve().parent.parent

READER = (
    HARNESS
    / "prompt12-production-local-fifo-reader.py"
)

LAUNCH = (
    HARNESS
    / "prompt12-production-provider-launch-materializer.py"
)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    return module


class ExplicitResumeCursorTests(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        cls.reader = load_module(
            READER,
            "prompt12_resume_reader",
        )

        cls.launch = load_module(
            LAUNCH,
            "prompt12_resume_launch",
        )

    @staticmethod
    def binding_paths():
        return [
            f"/tmp/T{index}.binding.json"
            for index in range(1, 7)
        ]

    def build_launch(self, index):
        return (
            self.launch
            .build_provider_launch_argv(
                experiment_id="EXP-TEST",
                run_id="RUN-TEST",
                fifo_path="/tmp/actuator.fifo",
                ratio_binding_paths=(
                    self.binding_paths()
                ),
                initial_transition_index=index,
            )
        )

    def test_launch_index_two_is_explicit(self):
        argv = self.build_launch(2)

        position = argv.index(
            "--initial-transition-index"
        )

        self.assertEqual(
            argv[position + 1],
            "2",
        )

    def test_binding_order_is_unchanged(self):
        argv = self.build_launch(2)

        position = argv.index(
            "--ratio-binding-paths-json"
        )

        paths = json.loads(
            argv[position + 1]
        )

        self.assertEqual(
            paths,
            self.binding_paths(),
        )

        self.assertTrue(
            paths[0].endswith(
                "T1.binding.json"
            )
        )

        self.assertTrue(
            paths[1].endswith(
                "T2.binding.json"
            )
        )

    def reader_argv(self, index=None):
        argv = [
            "--fifo-path",
            "/tmp/actuator.fifo",
            "--actuator-argv-json",
            '["/tmp/wrapper"]',
            "--experiment-id",
            "EXP-TEST",
            "--run-id",
            "RUN-TEST",
            "--ratio-binding-paths-json",
            json.dumps(
                self.binding_paths()
            ),
        ]

        if index is not None:
            argv.extend(
                [
                    "--initial-transition-index",
                    str(index),
                ]
            )

        return argv

    def test_reader_requires_explicit_cursor(self):
        with self.assertRaises(
            SystemExit
        ):
            self.reader.parse_args(
                self.reader_argv()
            )

    def test_reader_accepts_cursor_two(self):
        args = self.reader.parse_args(
            self.reader_argv(2)
        )

        self.assertEqual(
            args.initial_transition_index,
            2,
        )

    def test_reader_rejects_out_of_range(self):
        for value in (0, 7):
            with self.assertRaises(
                SystemExit
            ):
                self.reader.parse_args(
                    self.reader_argv(value)
                )

    def test_materializer_rejects_invalid_cursor(self):
        for value in (
            0,
            7,
            True,
            "2",
        ):
            with self.assertRaises(
                Exception
            ):
                self.build_launch(value)

    def test_reader_has_no_implicit_t1_cursor(self):
        source = READER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "next_transition_index = 1",
            source,
        )

        self.assertIn(
            "next_transition_index = initial_transition_index",
            source,
        )

    def test_index_two_selects_second_binding_expression(self):
        source = READER.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(source)

        functions = [
            node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == "run_reader"
        ]

        self.assertEqual(
            len(functions),
            1,
        )

        function_source = ast.unparse(
            functions[0]
        )

        self.assertIn(
            "next_transition_index = initial_transition_index",
            function_source,
        )

        self.assertIn(
            "ratio_binding_paths[next_transition_index - 1]",
            function_source,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
