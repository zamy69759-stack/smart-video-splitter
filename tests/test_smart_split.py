#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "smart_split.py"
SPEC = importlib.util.spec_from_file_location("smart_split", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ChooseBoundariesTests(unittest.TestCase):
    def test_prefers_nearby_scene_changes(self):
        result = MODULE.choose_boundaries(60.0, 3, [18.9, 41.2], 6.0)
        self.assertEqual(result, [0.0, 18.9, 41.2, 60.0])

    def test_falls_back_to_equal_targets(self):
        result = MODULE.choose_boundaries(60.0, 3, [], 6.0)
        self.assertEqual(result, [0.0, 20.0, 40.0, 60.0])

    def test_ignores_scene_outside_window(self):
        result = MODULE.choose_boundaries(60.0, 3, [8.0, 52.0], 5.0)
        self.assertEqual(result, [0.0, 20.0, 40.0, 60.0])


if __name__ == "__main__":
    unittest.main()

