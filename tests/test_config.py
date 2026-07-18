from __future__ import annotations
import os, tempfile, unittest
from pathlib import Path
from cleanzd import config
from cleanzd.config import ManifestEntry
from cleanzd.safety import SafetyError

class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["CLEAN_ZD_CONFIG_DIR"] = self.tmp
        self.target = Path.home() / f".cleanzd-test-{os.getpid()}"
        self.target.mkdir(exist_ok=True)

    def tearDown(self):
        os.environ.pop("CLEAN_ZD_CONFIG_DIR", None)
        self.target.rmdir()

    def test_add_and_load(self):
        config.manifest_add(ManifestEntry(path=str(self.target), strategy="empty-dir",
                                          reason="测试", decided_by="ai"))
        entries = config.load_manifest()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].decided_by, "ai")
        self.assertTrue(entries[0].added)  # 自动补日期

    def test_add_rejects_invalid(self):
        with self.assertRaises(SafetyError):
            config.manifest_add(ManifestEntry(path="/private/tmp", strategy="delete"))

    def test_add_rejects_duplicate(self):
        e = ManifestEntry(path=str(self.target), strategy="empty-dir")
        config.manifest_add(e)
        with self.assertRaises(SafetyError):
            config.manifest_add(ManifestEntry(path=str(self.target), strategy="delete"))

    def test_remove(self):
        config.manifest_add(ManifestEntry(path=str(self.target), strategy="empty-dir"))
        self.assertTrue(config.manifest_remove(str(self.target)))
        self.assertFalse(config.manifest_remove(str(self.target)))
        self.assertEqual(config.load_manifest(), [])

    def test_ignore_and_decided_paths(self):
        config.ignore_add("~/Library/Caches/keep-me", "用户说不清", "user")
        config.ignore_add("~/Library/Caches/keep-me", "重复", "user")  # 幂等
        self.assertEqual(len(config.load_ignore()), 1)
        self.assertIn(str(Path.home() / "Library/Caches/keep-me"), config.decided_paths())
