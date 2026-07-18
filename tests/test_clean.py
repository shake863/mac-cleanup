from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cleanzd import clean, config
from cleanzd.config import ManifestEntry


EMPTY_RULES = {
    "version": 1,
    "path_rules": [],
    "command_rules": [],
    "aliases": {},
}


class CleanTest(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        os.environ["CLEAN_ZD_CONFIG_DIR"] = self.cfg
        self.rules = Path(self.cfg) / "rules.json"
        self.rules.write_text(json.dumps(EMPTY_RULES))
        self.work = Path.home() / f".cleanzd-clean-test-{os.getpid()}"
        self.work.mkdir(exist_ok=True)

    def tearDown(self):
        os.environ.pop("CLEAN_ZD_CONFIG_DIR", None)
        import shutil

        shutil.rmtree(self.work, ignore_errors=True)

    def test_dry_run_counts_but_keeps(self):
        victim = self.work / "cache"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 1000)
        config.manifest_add(ManifestEntry(path=str(victim), strategy="delete"))
        report = clean.run_clean(dry_run=True, rules_path=self.rules)
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["total_bytes"], 1000)
        self.assertTrue(victim.exists())

    def test_real_clean_purge_removes_and_drops_delete_entry(self):
        victim = self.work / "onetime"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 10)
        config.manifest_add(ManifestEntry(path=str(victim), strategy="delete"))
        report = clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        self.assertFalse(victim.exists())
        self.assertEqual(report["freed_bytes"], 10)
        self.assertEqual(config.load_manifest(), [])

    def test_empty_dir_keeps_dir_and_entry(self):
        victim = self.work / "cachedir"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 10)
        config.manifest_add(ManifestEntry(path=str(victim), strategy="empty-dir"))
        clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        self.assertTrue(victim.exists())
        self.assertEqual(list(victim.iterdir()), [])
        self.assertEqual(len(config.load_manifest()), 1)

    def test_caution_skipped_by_default(self):
        victim = self.work / "risky"
        victim.mkdir()
        config.manifest_add(
            ManifestEntry(path=str(victim), strategy="delete", risk="caution")
        )
        clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        self.assertTrue(victim.exists())
        clean.run_clean(
            dry_run=False,
            purge=True,
            include_caution=True,
            rules_path=self.rules,
        )
        self.assertFalse(victim.exists())

    def test_history_written(self):
        clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        history = json.loads((Path(self.cfg) / "history.json").read_text())
        self.assertEqual(len(history), 1)

    def test_default_dispose_moves_to_trash(self):
        fake_home = self.work / "home"
        trash = fake_home / ".Trash"
        trash.mkdir(parents=True)
        victim = self.work / "trash-me"
        victim.write_text("x")
        with mock.patch("cleanzd.clean.Path.home", return_value=fake_home):
            clean.dispose(victim, purge=False)
        self.assertFalse(victim.exists())
        self.assertTrue((trash / "trash-me").exists())

    def test_rule_target_outside_home_is_rejected(self):
        unsafe_rules = {
            **EMPTY_RULES,
            "path_rules": [
                {
                    "id": "unsafe",
                    "title": "unsafe",
                    "tips": "test",
                    "paths": ["/private/tmp"],
                    "strategy": "delete",
                }
            ],
        }
        self.rules.write_text(json.dumps(unsafe_rules))
        items, _commands, warnings = clean.collect_items(rules_path=self.rules)
        self.assertEqual(items, [])
        self.assertTrue(any("[safety]" in warning for warning in warnings))


class IgnoreAndDedupTest(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        os.environ["CLEAN_ZD_CONFIG_DIR"] = self.cfg
        self.work = Path.home() / f".cleanzd-igdedup-test-{os.getpid()}"
        self.work.mkdir(exist_ok=True)
        self.rules_path = Path(self.cfg) / "rules.json"
        self.rules_path.write_text(json.dumps({
            "version": 1,
            "path_rules": [{"id": "t-work", "title": "t", "tips": "",
                            "strategy": "empty-dir", "paths": [str(self.work)]}],
            "command_rules": [], "aliases": {},
        }))

    def tearDown(self):
        os.environ.pop("CLEAN_ZD_CONFIG_DIR", None)
        import shutil
        shutil.rmtree(self.work, ignore_errors=True)

    def test_clean_respects_ignore(self):
        victim = self.work / "igdir"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 10)
        config.ignore_add(str(victim), "用户说不清", "user")
        items, _cmds, warns = clean.collect_items(rules_path=self.rules_path)
        self.assertEqual([i for i in items if str(i.path) == str(victim)], [])
        self.assertTrue(any("忽略名单" in w for w in warns))

    def test_ignore_covers_children(self):
        victim = self.work / "igdir2"
        sub = victim / "sub"
        sub.mkdir(parents=True)
        config.ignore_add(str(victim), "整个目录都不清", "user")
        items, _cmds, _warns = clean.collect_items(rules_path=self.rules_path)
        self.assertEqual([i for i in items if str(i.path).startswith(str(victim))], [])

    def test_rule_manifest_dedup(self):
        victim = self.work / "dupdir"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 10)
        config.manifest_add(ManifestEntry(path=str(victim), strategy="empty-dir"))
        items, _cmds, _warns = clean.collect_items(rules_path=self.rules_path)
        paths = [str(i.path) for i in items]
        self.assertEqual(paths.count(str(victim)), 1)
        self.assertNotIn(str(victim / "f"), paths)
