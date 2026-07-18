from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from cleanzd import paths


class ConfigDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = os.environ.get("CLEAN_ZD_CONFIG_DIR")
        os.environ["CLEAN_ZD_CONFIG_DIR"] = self.tmp

    def tearDown(self):
        if self.old is None:
            os.environ.pop("CLEAN_ZD_CONFIG_DIR", None)
        else:
            os.environ["CLEAN_ZD_CONFIG_DIR"] = self.old

    def test_config_dir_uses_env(self):
        self.assertEqual(paths.config_dir(), Path(self.tmp))

    def test_expand_user(self):
        self.assertEqual(paths.expand("~/x"), Path.home() / "x")


class HumanTest(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(paths.human(512), "512B")

    def test_gb(self):
        self.assertEqual(paths.human(3 * 1024**3), "3.0GB")


def _physical(path: Path) -> int:
    st = os.lstat(path)
    return st.st_blocks * 512


class PathSizeTest(unittest.TestCase):
    def test_dir_size_recursive(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a").write_bytes(b"x" * 100)
        (tmp / "sub").mkdir()
        (tmp / "sub" / "b").write_bytes(b"y" * 50)
        expected = _physical(tmp / "a") + _physical(tmp / "sub" / "b")
        self.assertEqual(paths.path_size(tmp), expected)

    def test_sparse_file_uses_physical_size(self):
        tmp = Path(tempfile.mkdtemp())
        sparse = tmp / "sparse.raw"
        with open(sparse, "wb") as f:
            f.seek(64 * 1024 * 1024)
            f.write(b"x")
        if _physical(sparse) >= os.lstat(sparse).st_size:
            self.skipTest("filesystem does not create sparse files")
        self.assertEqual(paths.path_size(sparse), _physical(sparse))
        self.assertLess(paths.path_size(sparse), 1024 * 1024)

    def test_missing_path_is_zero(self):
        self.assertEqual(paths.path_size(Path("/nonexistent/xyz")), 0)
