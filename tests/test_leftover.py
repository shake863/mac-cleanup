from __future__ import annotations

import unittest

from cleanzd.scan.leftover import is_orphan, vendor_prefixes


BUNDLES = {
    "com.tencent.xinWeChat",
    "com.apple.dt.Xcode",
    "com.jetbrains.intellij",
}
NAMES = {"wechat", "xcode", "intellij idea"}
VENDORS = vendor_prefixes(BUNDLES)


class VendorTest(unittest.TestCase):
    def test_prefixes(self):
        self.assertIn("com.tencent", VENDORS)
        self.assertIn("com.jetbrains", VENDORS)


class OrphanTest(unittest.TestCase):
    def check(self, name):
        return is_orphan(name, BUNDLES, NAMES, VENDORS, set())

    def test_installed_bundle_not_orphan(self):
        self.assertIsNone(self.check("com.tencent.xinWeChat"))

    def test_vendor_protection(self):
        self.assertIsNone(self.check("com.tencent.QQMusicMac"))

    def test_apple_excluded(self):
        self.assertIsNone(self.check("com.apple.gone.app.cache"))

    def test_orphan_detected(self):
        self.assertIsNotNone(self.check("com.sketchup.SketchUp.2021"))

    def test_non_bundle_name_skipped(self):
        self.assertIsNone(self.check("SomeRandomFolder"))

    def test_alias_owned(self):
        self.assertIsNone(
            is_orphan(
                "com.youdao.YoudaoDict",
                BUNDLES,
                NAMES,
                VENDORS,
                {"com.youdao.YoudaoDict"},
            )
        )

    def test_name_prefix_match(self):
        self.assertIsNone(self.check("com.jetbrains.intellij.idea.backend"))
