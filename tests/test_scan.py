from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from unittest import mock
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

class CacheScannerTest(unittest.TestCase):
    def test_scan_roots_reports_dirs_over_1mb(self):
        from cleanzd.scan import cache
        tmp = Path(tempfile.mkdtemp())
        big = tmp / "com.example.app"
        big.mkdir()
        (big / "blob").write_bytes(b"x" * (2 * 1024 * 1024))
        small = tmp / "tiny.app.cache"
        small.mkdir()
        (small / "blob").write_bytes(b"x" * 10)
        out = cache._scan_roots([str(tmp)], "测试来源")
        self.assertEqual([c.path for c in out], [str(big)])
        self.assertEqual(out[0].category, "cache")
        self.assertEqual(out[0].suggested_strategy, "empty-dir")

    def test_scan_skips_darwin_user_cache_dir(self):
        # DARWIN_USER_CACHE_DIR 解析到 /private/var/folders,在 $HOME 之外,
        # manifest add 必然拒绝;扫描产出这类候选只会成为每次都在的噪音。
        from cleanzd.scan import cache
        home = Path(tempfile.mkdtemp())
        dud = Path(tempfile.mkdtemp())
        blob_dir = dud / "com.example.app"
        blob_dir.mkdir()
        (blob_dir / "blob").write_bytes(b"x" * (2 * 1024 * 1024))
        fake = mock.Mock(stdout=str(dud) + "\n")
        with mock.patch.dict(os.environ, {"HOME": str(home)}), \
                mock.patch("subprocess.run", return_value=fake):
            out = cache.scan()
        self.assertFalse([c for c in out if c.path.startswith(str(dud))])

class BigfileScannerTest(unittest.TestCase):
    def test_threshold(self):
        from cleanzd.scan import bigfile
        tmp = Path(tempfile.mkdtemp())
        (tmp / "big.dmg").write_bytes(b"x" * (2 * 1024 * 1024))
        (tmp / "small.txt").write_bytes(b"x" * 10)
        out = bigfile._scan([str(tmp)], 1 * 1024 * 1024)
        self.assertEqual([Path(c.path).name for c in out], ["big.dmg"])
        self.assertEqual(out[0].risk, "caution")
        self.assertIn("天前", out[0].evidence)

    def test_unreadable_root_is_skipped(self):
        from cleanzd.scan import bigfile

        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(Path, "iterdir", side_effect=PermissionError):
            self.assertEqual(bigfile._scan([str(tmp)], 1), [])
