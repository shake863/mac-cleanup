from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from cleanzd.rules import PathRule, rule_targets


class RuleTargetsTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "a.log").write_bytes(b"x" * 200)
        (self.base / "b.txt").write_bytes(b"x" * 200)
        (self.base / "keep").mkdir()
        (self.base / "keep" / "c.log").write_bytes(b"x" * 200)

    def rule(self, **kwargs):
        defaults = {"id": "t", "title": "t", "tips": "", "paths": [str(self.base)]}
        defaults.update(kwargs)
        return PathRule(**defaults)

    def test_depth_default_by_strategy(self):
        self.assertEqual(self.rule(strategy="empty-dir").effective_depth(), 1)
        self.assertEqual(self.rule(strategy="delete").effective_depth(), 0)

    def test_depth0_targets_base(self):
        self.assertEqual(rule_targets(self.rule(strategy="delete")), [self.base])

    def test_depth1_lists_children(self):
        names = {path.name for path in rule_targets(self.rule(strategy="empty-dir"))}
        self.assertEqual(names, {"a.log", "b.txt", "keep"})

    def test_match_filters_names(self):
        names = {
            path.name
            for path in rule_targets(self.rule(strategy="empty-dir", match="*.log"))
        }
        self.assertEqual(names, {"a.log"})

    def test_recursive_files(self):
        names = {
            path.name
            for path in rule_targets(self.rule(depth=-1, match="*.log"))
        }
        self.assertEqual(names, {"a.log", "c.log"})

    def test_exclude(self):
        names = {
            path.name
            for path in rule_targets(
                self.rule(strategy="empty-dir", exclude=[str(self.base / "keep")])
            )
        }
        self.assertEqual(names, {"a.log", "b.txt"})

    def test_min_size(self):
        names = {
            path.name
            for path in rule_targets(self.rule(strategy="empty-dir", min_size=1000))
        }
        self.assertEqual(names, {"keep"})

    def test_older_than_days(self):
        old = self.base / "a.log"
        old_time = time.time() - 10 * 86400
        os.utime(old, (old_time, old_time))
        names = {
            path.name
            for path in rule_targets(
                self.rule(strategy="empty-dir", older_than_days=5)
            )
        }
        self.assertEqual(names, {"a.log"})

    def test_glob_in_paths(self):
        rule = self.rule(paths=[str(self.base / "*.log")], strategy="delete")
        self.assertEqual([path.name for path in rule_targets(rule)], ["a.log"])

    def test_missing_base_yields_nothing(self):
        rule = self.rule(paths=["/nonexistent/xyz"], strategy="delete")
        self.assertEqual(rule_targets(rule), [])

    def test_unreadable_base_yields_nothing(self):
        rule = self.rule(strategy="empty-dir")
        with mock.patch.object(Path, "iterdir", side_effect=PermissionError):
            self.assertEqual(rule_targets(rule), [])
