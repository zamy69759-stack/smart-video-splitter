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
    def test_prefers_speech_pauses(self):
        boundaries, sources = MODULE.choose_boundaries(60, 3, [19.2, 40.8], [18.9, 41.2], 6)
        self.assertEqual(boundaries, [0.0, 19.2, 40.8, 60])
        self.assertEqual(sources[1:3], ["speech_pause", "speech_pause"])

    def test_uses_scenes_without_pauses(self):
        boundaries, sources = MODULE.choose_boundaries(60, 3, [], [18.9, 41.2], 6)
        self.assertEqual(boundaries, [0.0, 18.9, 41.2, 60])
        self.assertEqual(sources[1:3], ["scene_change", "scene_change"])

    def test_falls_back_to_equal_targets(self):
        boundaries, sources = MODULE.choose_boundaries(60, 3, [], [], 6)
        self.assertEqual(boundaries, [0.0, 20.0, 40.0, 60])
        self.assertEqual(sources[1:3], ["equal_fallback", "equal_fallback"])

    def test_ignores_candidates_outside_window(self):
        boundaries, _ = MODULE.choose_boundaries(60, 3, [8], [52], 5)
        self.assertEqual(boundaries, [0.0, 20.0, 40.0, 60])


if __name__ == "__main__":
    unittest.main()

