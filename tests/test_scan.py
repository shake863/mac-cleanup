from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from cleanzd.scan import Candidate, render_json, render_table, run_scan, _admit

class AdmitTest(unittest.TestCase):
    def test_filters_seen_and_safety(self):
        seen = {str(Path.home() / "Library/Caches/decided")}
        cands = [
            Candidate(str(Path.home() / "Library/Caches/decided"), "cache", 1, "", "recommend", "empty-dir"),
            Candidate(str(Path.home() / "Library/Caches/com.apple.dock"), "cache", 1, "", "recommend", "empty-dir"),
            Candidate(str(Path.home() / "Library/Caches/fresh"), "cache", 1, "", "recommend", "empty-dir"),
        ]
        out = _admit(cands, seen)
        self.assertEqual([c.path for c in out], [str(Path.home() / "Library/Caches/fresh")])

class RenderTest(unittest.TestCase):
    def test_json_roundtrip(self):
        c = Candidate("/x", "cache", 42, "证据", "recommend", "empty-dir")
        data = json.loads(render_json([c]))
        self.assertEqual(data[0]["size"], 42)
        self.assertEqual(data[0]["evidence"], "证据")

    def test_table_contains_path(self):
        c = Candidate("/x/y", "cache", 42, "", "recommend", "empty-dir")
        self.assertIn("/x/y", render_table([c]))

class RunScanTest(unittest.TestCase):
    def setUp(self):
        os.environ["CLEAN_ZD_CONFIG_DIR"] = tempfile.mkdtemp()

    def tearDown(self):
        os.environ.pop("CLEAN_ZD_CONFIG_DIR", None)

    def test_empty_categories_ok(self):
        self.assertEqual(run_scan(categories=[]), [])
