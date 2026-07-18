from __future__ import annotations
import json, os, tempfile, time, unittest
from pathlib import Path
from unittest import mock

from cleanzd.analyze import (
    AnalyzeError,
    detect_signature,
    classify_kind,
    render_json,
    render_table,
    run_analyze,
)


def _make_home() -> Path:
    # macOS 下 /var 是 /private/var 的软链,先 resolve 便于路径断言
    return Path(tempfile.mkdtemp()).resolve()


def _fill(path: Path, nbytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * nbytes)


class SignatureTest(unittest.TestCase):
    def test_node_modules_needs_package_json_sibling(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "proj" / "node_modules"
        target.mkdir(parents=True)
        self.assertIsNone(detect_signature(target))
        (tmp / "proj" / "package.json").write_text("{}")
        sig = detect_signature(target)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.name, "node_modules")
        self.assertTrue(sig.rebuildable)

    def test_build_dir_without_marker_is_not_artifact(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "photos" / "build"
        target.mkdir(parents=True)
        self.assertIsNone(detect_signature(target))

    def test_gradle_build(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "app" / "build"
        target.mkdir(parents=True)
        (tmp / "app" / "build.gradle.kts").write_text("")
        sig = detect_signature(target)
        self.assertEqual(sig.name, "gradle-build")

    def test_cargo_target(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "rs" / "target"
        target.mkdir(parents=True)
        (tmp / "rs" / "Cargo.toml").write_text("")
        self.assertEqual(detect_signature(target).name, "cargo-target")

    def test_python_venv_by_pyvenv_cfg(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "anything"
        target.mkdir()
        (target / "pyvenv.cfg").write_text("home = /usr/bin")
        self.assertEqual(detect_signature(target).name, "python-venv")

    def test_named_venv_needs_bin_python(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / ".venv"
        target.mkdir()
        self.assertIsNone(detect_signature(target))
        (target / "bin").mkdir()
        (target / "bin" / "python").write_text("")
        self.assertEqual(detect_signature(target).name, "python-venv")

    def test_conda_env(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "miniconda3" / "envs" / "ml"
        target.mkdir(parents=True)
        self.assertEqual(detect_signature(target).name, "conda-env")


class KindTest(unittest.TestCase):
    def test_git_repo_is_dev_project(self):
        tmp = Path(tempfile.mkdtemp())
        proj = tmp / "proj"
        (proj / ".git").mkdir(parents=True)
        self.assertEqual(classify_kind(proj, home=tmp), "dev-project")

    def test_library_caches_is_cache(self):
        home = _make_home()
        target = home / "Library" / "Caches" / "com.example"
        target.mkdir(parents=True)
        self.assertEqual(classify_kind(target, home=home), "cache")

    def test_library_other_is_app_data(self):
        home = _make_home()
        target = home / "Library" / "Application Support" / "App"
        target.mkdir(parents=True)
        self.assertEqual(classify_kind(target, home=home), "app-data")

    def test_documents_is_user_data(self):
        home = _make_home()
        target = home / "Documents"
        target.mkdir(parents=True)
        self.assertEqual(classify_kind(target, home=home), "user-data")

    def test_unknown(self):
        home = _make_home()
        target = home / "mystery"
        target.mkdir(parents=True)
        self.assertEqual(classify_kind(target, home=home), "unknown")


class RunAnalyzeTest(unittest.TestCase):
    def test_single_level_percent_and_sort(self):
        home = _make_home()
        root = home / "work"
        _fill(root / "big" / "blob", 3 * 1024 * 1024)
        _fill(root / "small" / "blob", 1 * 1024 * 1024)
        report = run_analyze(str(root), top=20, min_size_mb=0, home=home)
        self.assertEqual(report["dir"], str(root))
        self.assertEqual(report["total"], 4 * 1024 * 1024)
        names = [Path(i["path"]).name for i in report["items"]]
        self.assertEqual(names, ["big", "small"])
        self.assertAlmostEqual(report["items"][0]["percent"], 75.0, places=1)

    def test_signature_fields_in_report(self):
        home = _make_home()
        root = home / "work" / "proj"
        _fill(root / "node_modules" / "blob", 2 * 1024 * 1024)
        (root / "package.json").write_text("{}")
        report = run_analyze(str(root), top=20, min_size_mb=0, home=home)
        item = next(
            i for i in report["items"] if Path(i["path"]).name == "node_modules"
        )
        self.assertEqual(item["kind"], "dev-artifact")
        self.assertEqual(item["signature"], "node_modules")
        self.assertTrue(item["rebuildable"])
        self.assertIn("npm", item["hint"])

    def test_age_uses_project_anchor_for_artifacts(self):
        home = _make_home()
        root = home / "work" / "proj"
        _fill(root / "node_modules" / "blob", 1024)
        marker = root / "package.json"
        marker.write_text("{}")
        old = time.time() - 400 * 86400
        os.utime(root / "node_modules", (old, old))
        os.utime(marker, (time.time(), time.time()))
        report = run_analyze(str(root), top=20, min_size_mb=0, home=home)
        item = next(
            i for i in report["items"] if Path(i["path"]).name == "node_modules"
        )
        self.assertLess(item["age_days"], 2)

    def test_age_uses_git_head_for_dev_project(self):
        home = _make_home()
        root = home / "work"
        proj = root / "proj"
        _fill(proj / ".git" / "HEAD", 64)
        old = time.time() - 400 * 86400
        os.utime(proj, (old, old))
        report = run_analyze(str(root), top=20, min_size_mb=0, home=home)
        item = report["items"][0]
        self.assertEqual(item["kind"], "dev-project")
        self.assertLess(item["age_days"], 2)

    def test_min_size_and_top_report_omitted(self):
        home = _make_home()
        root = home / "work"
        _fill(root / "a" / "blob", 3 * 1024 * 1024)
        _fill(root / "b" / "blob", 2 * 1024 * 1024)
        _fill(root / "c" / "blob", 1 * 1024)
        report = run_analyze(str(root), top=1, min_size_mb=1, home=home)
        self.assertEqual(len(report["items"]), 1)
        self.assertEqual(report["omitted"]["count"], 2)
        expected = sum(
            os.lstat(root / sub / "blob").st_blocks * 512 for sub in ("a", "b", "c")
        )
        self.assertEqual(report["total"], expected)

    def test_rejects_outside_home(self):
        home = _make_home()
        outside = Path(tempfile.mkdtemp())
        with self.assertRaises(AnalyzeError):
            run_analyze(str(outside), home=home)

    def test_rejects_symlink_escape(self):
        home = _make_home()
        outside = Path(tempfile.mkdtemp())
        link = home / "escape"
        link.symlink_to(outside)
        with self.assertRaises(AnalyzeError):
            run_analyze(str(link), home=home)

    def test_rejects_missing_and_files(self):
        home = _make_home()
        with self.assertRaises(AnalyzeError):
            run_analyze(str(home / "nope"), home=home)
        f = home / "f.txt"
        f.write_text("x")
        with self.assertRaises(AnalyzeError):
            run_analyze(str(f), home=home)

    def test_home_itself_is_allowed(self):
        home = _make_home()
        _fill(home / "d" / "blob", 1024)
        report = run_analyze(str(home), top=20, min_size_mb=0, home=home)
        self.assertEqual(len(report["items"]), 1)

    def test_unreadable_dir_raises_analyze_error(self):
        home = _make_home()
        (home / "d").mkdir()
        with mock.patch.object(Path, "iterdir", side_effect=PermissionError):
            with self.assertRaises(AnalyzeError):
                run_analyze(str(home / "d"), home=home)


class RenderTest(unittest.TestCase):
    def _report(self):
        home = _make_home()
        root = home / "work" / "proj"
        _fill(root / "node_modules" / "blob", 2 * 1024 * 1024)
        (root / "package.json").write_text("{}")
        return run_analyze(str(root), top=20, min_size_mb=0, home=home)

    def test_json_roundtrip(self):
        data = json.loads(render_json(self._report()))
        self.assertIn("items", data)
        self.assertIn("total_human", data)

    def test_table_mentions_signature_and_percent(self):
        text = render_table(self._report())
        self.assertIn("node_modules", text)
        self.assertIn("%", text)


class CliTest(unittest.TestCase):
    def test_analyze_subcommand_json(self):
        from cleanzd.__main__ import main

        home = _make_home()
        root = home / "work"
        _fill(root / "d" / "blob", 2 * 1024 * 1024)
        with mock.patch("cleanzd.analyze.Path.home", return_value=home):
            import io, contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(["analyze", str(root), "--json", "--min-size", "0"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["dir"], str(root))


if __name__ == "__main__":
    unittest.main()
