from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cleanzd.safety import SafetyError, safety_hit, validate_target


class SafetyHitTest(unittest.TestCase):
    def test_dock_cache_hit(self):
        path = Path.home() / "Library/Caches/com.apple.dock.iconcache"
        self.assertIsNotNone(safety_hit(path))

    def test_substring_hit(self):
        self.assertIsNotNone(safety_hit(Path.home() / "Music/Logic Pro/samples"))

    def test_normal_cache_no_hit(self):
        path = Path.home() / "Library/Caches/com.tencent.xinWeChat"
        self.assertIsNone(safety_hit(path))

    def test_system_temp_critical_cache_hit(self):
        cache_dir = Path("/private/var/folders/aa/hash/C")
        names = (
            "com.apple.dock.extra",
            "com.apple.FontRegistry",
            "com.apple.Spotlight",
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(safety_hit(cache_dir / name))

    def test_normal_system_temp_cache_no_hit(self):
        path = Path("/private/var/folders/aa/hash/C/com.tencent.xinWeChat")
        self.assertIsNone(safety_hit(path))


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        (self.home / "Library/Caches/foo").mkdir(parents=True)

    def test_ok(self):
        target = self.home / "Library/Caches/foo"
        self.assertEqual(validate_target(target, home=self.home), target.resolve())

    def test_reject_missing(self):
        with self.assertRaises(SafetyError):
            validate_target(self.home / "nope", home=self.home)

    def test_reject_outside_home(self):
        with self.assertRaises(SafetyError):
            validate_target(Path("/private/tmp"), home=self.home)

    def test_reject_home_itself(self):
        with self.assertRaises(SafetyError):
            validate_target(self.home, home=self.home)

    def test_reject_glob(self):
        with self.assertRaises(SafetyError):
            validate_target(self.home / "Library/Caches/*", home=self.home)

    def test_reject_symlink_escape(self):
        link = self.home / "escape"
        link.symlink_to("/private/tmp")
        with self.assertRaises(SafetyError):
            validate_target(link, home=self.home)
