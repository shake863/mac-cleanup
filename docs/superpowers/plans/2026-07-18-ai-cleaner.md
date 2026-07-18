# clean-zd v2(AI 驱动 Mac 清理助手)实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 clean-zd 从 Bash 单文件重写为 Python 三层架构引擎(scan / manifest / clean / status),并交付 market-zd 中的 skill 薄壳,实现 AI 驱动的扫描-判断-记录-复用清理闭环。

**Architecture:** 执行层 Python stdlib-only CLI(确定性、无 AI、硬编码安全守卫);知识层 JSON(仓库 rules.json + 本机 `~/.config/clean-zd/` 的 manifest/ignore);智能层 skill(工作流,AI 只能写清单、永不直接删)。规格见 `docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`,知识种子见 `docs/reference/lemon-cleaner-knowledge.md`。

**Tech Stack:** Python ≥ 3.9(macOS 自带 `/usr/bin/python3`),仅标准库;测试用 `unittest`。

## Global Constraints

- 仅 Python 标准库,兼容 Python 3.9:每个模块首行 `from __future__ import annotations`(否则 `X | None` 注解在 3.9 崩)。
- 测试一律 `python3 -m unittest discover -s tests -v`,在仓库根目录运行;**测试绝不触碰真实用户数据**:所有涉及配置目录的测试通过环境变量 `CLEAN_ZD_CONFIG_DIR` 指向 `tempfile.mkdtemp()`,涉及文件树的测试自建临时树。
- 删除默认进废纸篓(`~/.Trash`),`--purge` 才真删;`risk=caution` 的规则/条目默认跳过,`--include-caution` 才执行。
- 引擎绝不删除 `$HOME` 之外的路径;v1 规则库只收用户可写路径(旧 Bash 中需 root 的块有意放弃,见 Task 10 清单)。
- CLI 用户可见输出用中文;commit message 用中文、结尾带 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。
- 完成整个计划后按仓库约定补 `docs/dev-log/2026-07-18-<主题>.md`(Task 10/11 内含)。

## 文件结构(全景)

```
clean-zd                      # Python 启动器(Task 1 用它替换 Bash 同名文件;Bash 先移 legacy/)
legacy/clean-zd.bash          # 原 Bash 脚本(Task 1 移入,Task 10 对比后删除)
cleanzd/
  __init__.py                 # __version__
  __main__.py                 # argparse CLI 分发
  paths.py                    # 配置目录/展开/体积/human
  safety.py                   # 安全排除名单 + validate_target
  config.py                   # manifest.json / ignore.json 存取
  rules.py                    # 规则加载与求值
  rules.json                  # 规则库(Bash 转译 + lemon 知识)
  clean.py                    # 清理执行器(dry-run/真删/命令规则)
  status.py                   # 概况
  scan/
    __init__.py               # Candidate、编排、过滤、渲染
    cache.py  dev.py  leftover.py  bigfile.py  systemitems.py
tests/
  test_paths.py test_safety.py test_config.py test_rules.py
  test_rules_data.py test_clean.py test_scan.py test_leftover.py test_cli.py
```

---

### Task 1: 包骨架、CLI 分发与 paths 工具

**Files:**
- Move: `clean-zd` → `legacy/clean-zd.bash`(git mv,保留可执行位)
- Create: `clean-zd`(新启动器)、`cleanzd/__init__.py`、`cleanzd/__main__.py`、`cleanzd/paths.py`、`tests/test_paths.py`、`tests/test_cli.py`

**Interfaces:**
- Produces: `paths.config_dir() -> Path`(尊重 `CLEAN_ZD_CONFIG_DIR` 环境变量,自动 mkdir)、`paths.expand(raw: str) -> Path`(expandvars+expanduser,不 resolve)、`paths.human(nbytes: int) -> str`、`paths.path_size(p: Path) -> int`(文件取 lstat,目录递归求和,容错)。`__main__.main(argv=None) -> int`,四个子命令 scan/manifest/clean/status(本任务先接 paths 无关的 stub,后续任务逐个接实现)。

- [ ] **Step 1: 移走 Bash 脚本**

```bash
mkdir -p legacy && git mv clean-zd legacy/clean-zd.bash
```

- [ ] **Step 2: 写失败测试**

`tests/test_paths.py`:

```python
from __future__ import annotations
import os, tempfile, unittest
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

class PathSizeTest(unittest.TestCase):
    def test_dir_size_recursive(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "a").write_bytes(b"x" * 100)
        (tmp / "sub").mkdir()
        (tmp / "sub" / "b").write_bytes(b"y" * 50)
        self.assertEqual(paths.path_size(tmp), 150)

    def test_missing_path_is_zero(self):
        self.assertEqual(paths.path_size(Path("/nonexistent/xyz")), 0)
```

`tests/test_cli.py`:

```python
from __future__ import annotations
import unittest
from cleanzd.__main__ import main

class CliTest(unittest.TestCase):
    def test_no_args_exits_2(self):
        with self.assertRaises(SystemExit):
            main([])

    def test_status_runs(self):
        self.assertEqual(main(["status"]), 0)
```

- [ ] **Step 3: 跑测试确认失败**

Run: `python3 -m unittest discover -s tests -v`
Expected: `ModuleNotFoundError: No module named 'cleanzd'`

- [ ] **Step 4: 实现**

`cleanzd/__init__.py`:

```python
__version__ = "2.0.0-dev"
```

`cleanzd/paths.py`:

```python
from __future__ import annotations
import os
from pathlib import Path

def config_dir() -> Path:
    env = os.environ.get("CLEAN_ZD_CONFIG_DIR")
    d = Path(env) if env else Path.home() / ".config" / "clean-zd"
    d.mkdir(parents=True, exist_ok=True)
    return d

def expand(raw: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(raw)))

def human(nbytes: int) -> str:
    size = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)}B" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

def path_size(p: Path) -> int:
    try:
        if p.is_symlink() or p.is_file():
            return p.lstat().st_size
        if not p.is_dir():
            return 0
        total = 0
        for root, _dirs, files in os.walk(p, onerror=lambda e: None):
            for name in files:
                try:
                    total += os.lstat(os.path.join(root, name)).st_size
                except OSError:
                    pass
        return total
    except OSError:
        return 0
```

`cleanzd/__main__.py`(本任务 status 打印占位,后续任务替换 dispatch 内容):

```python
from __future__ import annotations
import argparse, sys

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clean-zd", description="AI 驱动的 Mac 清理助手(引擎)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="只读扫描,输出候选清理项")
    p_scan.add_argument("--category", action="append",
                        choices=["cache", "dev", "leftover", "bigfile", "system"])
    p_scan.add_argument("--json", action="store_true")
    p_scan.add_argument("--threshold-mb", type=int, default=500)
    p_scan.add_argument("--dir", action="append")

    p_m = sub.add_parser("manifest", help="本机清单管理")
    msub = p_m.add_subparsers(dest="mcmd", required=True)
    m_add = msub.add_parser("add", help="登记可清条目(写入前安全校验)")
    m_add.add_argument("path")
    m_add.add_argument("--strategy", required=True, choices=["empty-dir", "delete"])
    m_add.add_argument("--risk", default="recommend", choices=["recommend", "caution"])
    m_add.add_argument("--type", default="cache",
                       choices=["cache", "dev", "leftover", "bigfile", "system"])
    m_add.add_argument("--reason", default="")
    m_add.add_argument("--decided-by", default="user", choices=["ai", "user"])
    m_rm = msub.add_parser("remove", help="移除清单条目")
    m_rm.add_argument("path")
    m_ls = msub.add_parser("list", help="列出清单与忽略名单")
    m_ls.add_argument("--json", action="store_true")
    m_ig = msub.add_parser("ignore", help="登记不清条目(扫描不再出现)")
    m_ig.add_argument("path")
    m_ig.add_argument("--reason", default="")
    m_ig.add_argument("--decided-by", default="user", choices=["ai", "user"])

    p_c = sub.add_parser("clean", help="按规则库+清单执行清理")
    p_c.add_argument("--dry-run", action="store_true")
    p_c.add_argument("--purge", action="store_true", help="不进废纸篓,直接删除")
    p_c.add_argument("--include-caution", action="store_true")
    p_c.add_argument("--json", action="store_true")

    sub.add_parser("status", help="清单与清理历史概况")
    return parser

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        print("clean-zd v2 引擎骨架就绪(status 将在后续任务实现)")
        return 0
    print(f"子命令 {args.cmd} 尚未实现", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
```

新 `clean-zd` 启动器(根目录,`chmod +x`):

```python
#!/usr/bin/env python3
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cleanzd.__main__ import main
sys.exit(main())
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全部 PASS(7 个测试)。再手工 `./clean-zd status` 确认输出占位文案、退出码 0。

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: v2 Python 引擎骨架(CLI 分发 + paths 工具),Bash 移入 legacy/"
```

---

### Task 2: safety 安全模块

**Files:**
- Create: `cleanzd/safety.py`、`tests/test_safety.py`

**Interfaces:**
- Consumes: `paths.expand`
- Produces: `SafetyError(Exception)`;`safety_hit(p: Path) -> str | None`(命中安全排除名单返回命中的模式,否则 None);`validate_target(p: Path, home: Path | None = None) -> Path`(校验通过返回 resolve 后路径,否则抛 SafetyError)。校验规则:不含通配符、路径存在、resolve 后在 home 内、非 home 本身/根、不命中排除名单(原始与 resolve 后都查)。名单出处:`docs/reference/lemon-cleaner-knowledge.md` §1.1/§1.2。

- [ ] **Step 1: 写失败测试**

`tests/test_safety.py`:

```python
from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from cleanzd.safety import SafetyError, safety_hit, validate_target

class SafetyHitTest(unittest.TestCase):
    def test_dock_cache_hit(self):
        p = Path.home() / "Library/Caches/com.apple.dock.iconcache"
        self.assertIsNotNone(safety_hit(p))

    def test_substring_hit(self):
        self.assertIsNotNone(safety_hit(Path.home() / "Music/Logic Pro/samples"))

    def test_normal_cache_no_hit(self):
        self.assertIsNone(safety_hit(Path.home() / "Library/Caches/com.tencent.xinWeChat"))

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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_safety -v`
Expected: `ModuleNotFoundError: No module named 'cleanzd.safety'`

- [ ] **Step 3: 实现 `cleanzd/safety.py`**

```python
from __future__ import annotations
import fnmatch
from pathlib import Path
from .paths import expand

class SafetyError(Exception):
    """路径未通过安全校验。"""

# 出处与原因见 docs/reference/lemon-cleaner-knowledge.md §1.1(系统关键缓存)/§1.2(应用数据混在缓存目录)
SAFETY_GLOBS = (
    "~/Library/Caches/com.apple.dock*",
    "~/Library/Caches/com.apple.appstore*",
    "~/Library/Caches/com.apple.FontRegistry*",
    "~/Library/Caches/com.apple.LaunchServices-*",
    "~/Library/Caches/com.apple.IconServices*",
    "~/Library/Caches/com.apple.Spotlight*",
    "~/Library/Caches/Desktop Pictures*",
    "~/Library/Caches/ColorSync*",
    "~/Library/Caches/com.apple.preference.desktopscreeneffect.desktop*",
    "~/Library/Caches/codes.rambo.AirCore*",
    "~/Library/Caches/com.rovio.mac.badpiggies*",
    "~/Library/Caches/com.naturalmotion.csrracingmac*",
    "~/Library/Caches/com.glu.macos.*",
    "~/Library/Caches/Axure-*",
    "~/Library/Application Support/Steam/steamapps/common*",
)
SAFETY_SUBSTRINGS = (
    "Logic Pro", "com.apple.logic", "com.apple.STMExtension",
    "1Password", "IINA", "Aerial", ".DocumentRevisions-V100", ".app/",
)

def safety_hit(p: Path) -> str | None:
    s = str(p)
    for pat in SAFETY_GLOBS:
        if fnmatch.fnmatch(s, str(expand(pat))):
            return pat
    for sub in SAFETY_SUBSTRINGS:
        if sub in s:
            return sub
    return None

def validate_target(p: Path, home: Path | None = None) -> Path:
    home = (home or Path.home()).resolve()
    raw = Path(str(p))
    if any(ch in str(raw) for ch in "*?["):
        raise SafetyError(f"路径不允许含通配符: {raw}")
    if not raw.exists() and not raw.is_symlink():
        raise SafetyError(f"路径不存在: {raw}")
    resolved = raw.resolve()
    if str(resolved) == "/" or resolved == home:
        raise SafetyError(f"拒绝根路径或家目录本身: {resolved}")
    if not resolved.is_relative_to(home):
        raise SafetyError(f"路径不在家目录内(或经软链逃逸): {raw} -> {resolved}")
    hit = safety_hit(raw) or safety_hit(resolved)
    if hit:
        raise SafetyError(f"命中安全排除名单({hit}): {raw}")
    return resolved
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_safety -v`
Expected: 9 个测试全 PASS。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/safety.py tests/test_safety.py
git commit -m "feat: safety 模块——排除名单(lemon 知识种子)与清单路径硬校验"
```

---

### Task 3: config 本机清单存取

**Files:**
- Create: `cleanzd/config.py`、`tests/test_config.py`

**Interfaces:**
- Consumes: `paths.config_dir/expand`、`safety.validate_target/SafetyError`
- Produces: `@dataclass ManifestEntry(path: str, strategy: str, risk: str = "recommend", type: str = "cache", reason: str = "", decided_by: str = "user", added: str = "")`;`load_manifest() -> list[ManifestEntry]`;`save_manifest(entries)`;`load_ignore() -> list[dict]`;`manifest_add(entry)`(校验+查重+补 added 日期);`manifest_remove(path: str) -> bool`;`ignore_add(path, reason, decided_by)`(幂等);`decided_paths() -> set[str]`(manifest∪ignore 的展开后路径字符串,供扫描过滤)。

- [ ] **Step 1: 写失败测试**

`tests/test_config.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_config -v`
Expected: `ModuleNotFoundError: No module named 'cleanzd.config'`

- [ ] **Step 3: 实现 `cleanzd/config.py`**

```python
from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from datetime import date
from .paths import config_dir, expand
from .safety import SafetyError, validate_target

MANIFEST = "manifest.json"
IGNORE = "ignore.json"

@dataclass
class ManifestEntry:
    path: str
    strategy: str               # empty-dir | delete
    risk: str = "recommend"     # recommend | caution
    type: str = "cache"         # cache|dev|leftover|bigfile|system
    reason: str = ""
    decided_by: str = "user"    # ai | user
    added: str = ""

def _load(name: str) -> list:
    f = config_dir() / name
    if not f.exists():
        return []
    return json.loads(f.read_text() or "[]")

def _save(name: str, items: list) -> None:
    (config_dir() / name).write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n")

def load_manifest() -> list[ManifestEntry]:
    return [ManifestEntry(**d) for d in _load(MANIFEST)]

def save_manifest(entries: list[ManifestEntry]) -> None:
    _save(MANIFEST, [asdict(e) for e in entries])

def load_ignore() -> list[dict]:
    return _load(IGNORE)

def manifest_add(entry: ManifestEntry) -> None:
    validate_target(expand(entry.path))
    entries = load_manifest()
    if any(e.path == entry.path for e in entries):
        raise SafetyError(f"清单中已存在: {entry.path}")
    if not entry.added:
        entry.added = date.today().isoformat()
    entries.append(entry)
    save_manifest(entries)

def manifest_remove(path: str) -> bool:
    entries = load_manifest()
    kept = [e for e in entries if e.path != path]
    if len(kept) == len(entries):
        return False
    save_manifest(kept)
    return True

def ignore_add(path: str, reason: str, decided_by: str) -> None:
    items = load_ignore()
    if any(i["path"] == path for i in items):
        return
    items.append({"path": path, "reason": reason, "decided_by": decided_by,
                  "added": date.today().isoformat()})
    _save(IGNORE, items)

def decided_paths() -> set[str]:
    out = {str(expand(e.path)) for e in load_manifest()}
    out |= {str(expand(i["path"])) for i in load_ignore()}
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_config -v`
Expected: 5 个测试全 PASS。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/config.py tests/test_config.py
git commit -m "feat: config 模块——manifest/ignore 本机清单存取与校验"
```

---

### Task 4: rules 规则引擎

**Files:**
- Create: `cleanzd/rules.py`、`tests/test_rules.py`

**Interfaces:**
- Consumes: `paths.expand`
- Produces: `@dataclass PathRule(id, title, tips, paths: list[str], risk="recommend", strategy="empty-dir", depth: int | None = None, match: str = "", exclude: list[str] = [], min_size: int = 0, older_than_days: int = 0)`,方法 `effective_depth() -> int`(显式 depth 优先;否则 empty-dir→1、delete→0);`@dataclass CommandRule(id, title, tips, command: list[str], guard: str, risk="recommend", dry_paths: list[str] = [])`;`rules_file() -> Path`(`cleanzd/rules.json`);`load_rules(path=None) -> tuple[list[PathRule], list[CommandRule], dict]`(第三项为 aliases);`rule_targets(rule: PathRule) -> list[Path]`(展开 paths 中的 glob → 按 depth 枚举 0=本身/1=子项/-1=递归文件 → 按 match/exclude/min_size/older_than_days 过滤)。

- [ ] **Step 1: 写失败测试**

`tests/test_rules.py`:

```python
from __future__ import annotations
import os, tempfile, time, unittest
from pathlib import Path
from cleanzd.rules import PathRule, rule_targets

class RuleTargetsTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "a.log").write_bytes(b"x" * 200)
        (self.base / "b.txt").write_bytes(b"x" * 200)
        (self.base / "keep").mkdir()
        (self.base / "keep" / "c.log").write_bytes(b"x" * 200)

    def rule(self, **kw):
        defaults = dict(id="t", title="t", tips="", paths=[str(self.base)])
        defaults.update(kw)
        return PathRule(**defaults)

    def test_depth_default_by_strategy(self):
        self.assertEqual(self.rule(strategy="empty-dir").effective_depth(), 1)
        self.assertEqual(self.rule(strategy="delete").effective_depth(), 0)

    def test_depth0_targets_base(self):
        self.assertEqual(rule_targets(self.rule(strategy="delete")), [self.base])

    def test_depth1_lists_children(self):
        names = {p.name for p in rule_targets(self.rule(strategy="empty-dir"))}
        self.assertEqual(names, {"a.log", "b.txt", "keep"})

    def test_match_filters_names(self):
        names = {p.name for p in rule_targets(self.rule(strategy="empty-dir", match="*.log"))}
        self.assertEqual(names, {"a.log"})

    def test_recursive_files(self):
        names = {p.name for p in rule_targets(self.rule(depth=-1, match="*.log"))}
        self.assertEqual(names, {"a.log", "c.log"})

    def test_exclude(self):
        names = {p.name for p in rule_targets(
            self.rule(strategy="empty-dir", exclude=[str(self.base / "keep")]))}
        self.assertEqual(names, {"a.log", "b.txt"})

    def test_min_size(self):
        names = {p.name for p in rule_targets(self.rule(strategy="empty-dir", min_size=1000))}
        self.assertEqual(names, {"keep"})  # min_size 只过滤文件,目录不受限

    def test_older_than_days(self):
        old = self.base / "a.log"
        os.utime(old, (time.time() - 10 * 86400, time.time() - 10 * 86400))
        names = {p.name for p in rule_targets(
            self.rule(strategy="empty-dir", older_than_days=5))}
        self.assertEqual(names, {"a.log"})

    def test_glob_in_paths(self):
        r = self.rule(paths=[str(self.base / "*.log")], strategy="delete")
        self.assertEqual([p.name for p in rule_targets(r)], ["a.log"])

    def test_missing_base_yields_nothing(self):
        r = self.rule(paths=["/nonexistent/xyz"], strategy="delete")
        self.assertEqual(rule_targets(r), [])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_rules -v`
Expected: `ModuleNotFoundError: No module named 'cleanzd.rules'`

- [ ] **Step 3: 实现 `cleanzd/rules.py`**

```python
from __future__ import annotations
import fnmatch, glob, json, time
from dataclasses import dataclass, field
from pathlib import Path
from .paths import expand

@dataclass
class PathRule:
    id: str
    title: str
    tips: str
    paths: list[str]
    risk: str = "recommend"
    strategy: str = "empty-dir"     # empty-dir | delete
    depth: int | None = None        # 0=本身 1=子项 -1=递归文件;默认由 strategy 决定
    match: str = ""
    exclude: list[str] = field(default_factory=list)
    min_size: int = 0
    older_than_days: int = 0

    def effective_depth(self) -> int:
        if self.depth is not None:
            return self.depth
        return 1 if self.strategy == "empty-dir" else 0

@dataclass
class CommandRule:
    id: str
    title: str
    tips: str
    command: list[str]
    guard: str
    risk: str = "recommend"
    dry_paths: list[str] = field(default_factory=list)

def rules_file() -> Path:
    return Path(__file__).with_name("rules.json")

def load_rules(path: Path | None = None):
    data = json.loads((path or rules_file()).read_text())
    prules = [PathRule(**d) for d in data.get("path_rules", [])]
    crules = [CommandRule(**d) for d in data.get("command_rules", [])]
    return prules, crules, data.get("aliases", {})

def _bases(rule: PathRule) -> list[Path]:
    out: list[Path] = []
    for raw in rule.paths:
        expanded = str(expand(raw))
        if any(ch in expanded for ch in "*?["):
            out += [Path(p) for p in sorted(glob.glob(expanded))]
        elif Path(expanded).exists():
            out.append(Path(expanded))
    return out

def _keep(rule: PathRule, p: Path) -> bool:
    if rule.match and not fnmatch.fnmatch(p.name, rule.match):
        return False
    for pat in rule.exclude:
        ep = str(expand(pat))
        if fnmatch.fnmatch(str(p), ep) or str(p).startswith(ep):
            return False
    try:
        st = p.lstat()
    except OSError:
        return False
    if rule.min_size and not p.is_dir() and st.st_size < rule.min_size:
        return False
    if rule.older_than_days and time.time() - st.st_mtime < rule.older_than_days * 86400:
        return False
    return True

def rule_targets(rule: PathRule) -> list[Path]:
    depth = rule.effective_depth()
    targets: list[Path] = []
    for base in _bases(rule):
        if depth == 0 or not base.is_dir():
            cand = [base]
        elif depth == 1:
            cand = sorted(base.iterdir())
        else:
            cand = sorted(p for p in base.rglob("*") if not p.is_dir())
        targets += [p for p in cand if _keep(rule, p)]
    return targets
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_rules -v`
Expected: 10 个测试全 PASS。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/rules.py tests/test_rules.py
git commit -m "feat: rules 规则引擎——加载与 depth/match/exclude/size/age 求值"
```

---

### Task 5: rules.json 规则库(Bash 转译 + lemon 知识)

**Files:**
- Create: `cleanzd/rules.json`、`tests/test_rules_data.py`

**Interfaces:**
- Consumes: `rules.load_rules`
- Produces: 可被 `load_rules()` 无异常加载的规则库。id 全局唯一;所有 path 规则路径均在 `~` 内。

- [ ] **Step 1: 写失败测试**

`tests/test_rules_data.py`:

```python
from __future__ import annotations
import unittest
from cleanzd.rules import load_rules

class RulesDataTest(unittest.TestCase):
    def test_loads_and_ids_unique(self):
        prules, crules, aliases = load_rules()
        ids = [r.id for r in prules] + [c.id for c in crules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(prules), 25)
        self.assertGreaterEqual(len(crules), 10)
        self.assertIsInstance(aliases, dict)

    def test_all_paths_in_home(self):
        prules, crules, _ = load_rules()
        for r in prules:
            for p in r.paths:
                self.assertTrue(p.startswith("~") or p.startswith("$"),
                                f"{r.id} 路径必须以 ~ 或 $ 开头: {p}")

    def test_risks_valid(self):
        prules, crules, _ = load_rules()
        for r in prules + crules:
            self.assertIn(r.risk, ("recommend", "caution"), r.id)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_rules_data -v`
Expected: `FileNotFoundError`(rules.json 不存在)

- [ ] **Step 3: 写 `cleanzd/rules.json`**

完整内容如下(转译自 `legacy/clean-zd.bash`;risk 标记与 tips 参照 `docs/reference/lemon-cleaner-knowledge.md` §3;需 root 的旧块有意放弃,见 Task 10):

```json
{
  "version": 1,
  "path_rules": [
    {"id": "trash", "title": "废纸篓", "tips": "清空前确认废纸篓内容确实不要", "risk": "caution", "strategy": "empty-dir", "paths": ["~/.Trash"]},
    {"id": "user-caches", "title": "用户缓存", "tips": "~/Library/Caches 下应用缓存,可再生;安全名单在引擎内强制排除", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Caches"]},
    {"id": "as-caches", "title": "Application Support/Caches", "tips": "部分应用写在这里的缓存", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Application Support/Caches"]},
    {"id": "mail-logs", "title": "Mail 日志", "tips": "邮件应用运行日志,可再生", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Containers/com.apple.mail/Data/Library/Logs/Mail"]},
    {"id": "coresim-logs", "title": "CoreSimulator 日志", "tips": "iOS 模拟器日志", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Logs/CoreSimulator"]},
    {"id": "jetbrains-logs", "title": "JetBrains 日志", "tips": "IDE 运行日志,可再生", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Logs/JetBrains"]},
    {"id": "adobe-media-cache", "title": "Adobe 媒体缓存", "tips": "Premiere 等渲染缓存,可再生但重建耗时", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Application Support/Adobe/Common/Media Cache Files"]},
    {"id": "chrome-app-cache", "title": "Chrome Application Cache", "tips": "只清 Application Cache,不碰 profile(书签/密码)", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Application Support/Google/Chrome/Default/Application Cache"]},
    {"id": "ios-apps", "title": "旧 iOS 应用安装包", "tips": "iTunes 同步遗留的 .ipa", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Music/iTunes/iTunes Media/Mobile Applications"]},
    {"id": "ios-backups", "title": "iOS 设备备份", "tips": "删除前确认设备已另有备份(lemon: recommend=NO)", "risk": "caution", "strategy": "empty-dir", "paths": ["~/Library/Application Support/MobileSync/Backup"]},
    {"id": "xcode-deriveddata", "title": "Xcode DerivedData", "tips": "构建产物,重建自动生成", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/DerivedData"]},
    {"id": "xcode-archives", "title": "Xcode Archives", "tips": "发布归档含 dSYM,删了无法符号化历史版本(lemon: recommend=NO)", "risk": "caution", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/Archives"]},
    {"id": "xcode-device-logs", "title": "Xcode 设备日志", "tips": "调试日志,可再生", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/iOS Device Logs"]},
    {"id": "xcode-doccache", "title": "Xcode 文档缓存", "tips": "可重新下载", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/DocumentationCache"]},
    {"id": "xcode-watchos-support", "title": "watchOS Device Support", "tips": "旧设备符号,连新设备会重建(lemon: recommend=NO)", "risk": "caution", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/watchOS DeviceSupport"]},
    {"id": "xcode-ib-sim", "title": "IB Support 模拟器设备", "tips": "Interface Builder 渲染用模拟器", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Developer/Xcode/UserData/IB Support/Simulator Devices"]},
    {"id": "coresim-devices", "title": "CoreSimulator 设备数据", "tips": "全部模拟器及其数据,删后需重建模拟器(lemon 对整个 CoreSimulator 标 recommend=NO)", "risk": "caution", "strategy": "empty-dir", "paths": ["~/Library/Developer/CoreSimulator/Devices"]},
    {"id": "dropbox-cache", "title": "Dropbox 缓存", "tips": "同步缓存,可再生", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Dropbox/.dropbox.cache"]},
    {"id": "gdrive-content-cache", "title": "Google Drive 内容缓存", "tips": "DriveFS 本地缓存,可再生", "risk": "recommend", "strategy": "delete", "paths": ["~/Library/Application Support/Google/DriveFS/*/content_cache"]},
    {"id": "steam-caches", "title": "Steam 缓存与日志", "tips": "只动缓存/日志/临时下载,不碰 steamapps/common 游戏本体", "risk": "recommend", "strategy": "delete", "paths": ["~/Library/Application Support/Steam/appcache", "~/Library/Application Support/Steam/depotcache", "~/Library/Application Support/Steam/logs", "~/Library/Application Support/Steam/steamapps/shadercache", "~/Library/Application Support/Steam/steamapps/temp", "~/Library/Application Support/Steam/steamapps/download"]},
    {"id": "minecraft-dirs", "title": "Minecraft 缓存目录", "tips": "日志/崩溃报告/网页缓存", "risk": "recommend", "strategy": "delete", "paths": ["~/Library/Application Support/minecraft/logs", "~/Library/Application Support/minecraft/crash-reports", "~/Library/Application Support/minecraft/webcache", "~/Library/Application Support/minecraft/webcache2", "~/Library/Application Support/minecraft/.mixin.out"]},
    {"id": "minecraft-logs", "title": "Minecraft 散落日志", "tips": "launcher 日志文件", "risk": "recommend", "strategy": "delete", "depth": 1, "match": "*.log", "paths": ["~/Library/Application Support/minecraft"]},
    {"id": "lunarclient", "title": "Lunar Client 缓存与日志", "tips": "游戏客户端缓存", "risk": "recommend", "strategy": "delete", "paths": ["~/.lunarclient/game-cache", "~/.lunarclient/launcher-cache", "~/.lunarclient/logs", "~/.lunarclient/offline/*/logs", "~/.lunarclient/offline/files/*/logs"]},
    {"id": "wget", "title": "Wget 日志与 HSTS", "tips": "wget 运行痕迹", "risk": "recommend", "strategy": "delete", "paths": ["~/wget-log", "~/.wget-hsts"]},
    {"id": "cacher-logs", "title": "Cacher 日志", "tips": "可再生", "risk": "recommend", "strategy": "delete", "paths": ["~/.cacher/logs"]},
    {"id": "android-cache", "title": "Android SDK 缓存", "tips": "可再生", "risk": "recommend", "strategy": "delete", "paths": ["~/.android/cache"]},
    {"id": "gradle-caches", "title": "Gradle 缓存", "tips": "依赖会重新下载,重建耗时", "risk": "recommend", "strategy": "delete", "paths": ["~/.gradle/caches"]},
    {"id": "kite-logs", "title": "Kite 日志", "tips": "可再生", "risk": "recommend", "strategy": "delete", "paths": ["~/.kite/logs"]},
    {"id": "tencent-meeting-logs", "title": "腾讯会议日志", "tips": "运行日志,可再生", "risk": "recommend", "strategy": "empty-dir", "paths": ["~/Library/Containers/com.tencent.meeting/Data/Library/Global/Logs"]},
    {"id": "teams-caches", "title": "Microsoft Teams 缓存", "tips": "清后 Teams 重置缓存,可修复性能问题", "risk": "recommend", "strategy": "delete", "paths": ["~/Library/Application Support/Microsoft/Teams/IndexedDB", "~/Library/Application Support/Microsoft/Teams/Cache", "~/Library/Application Support/Microsoft/Teams/Application Cache", "~/Library/Application Support/Microsoft/Teams/Code Cache", "~/Library/Application Support/Microsoft/Teams/blob_storage", "~/Library/Application Support/Microsoft/Teams/databases", "~/Library/Application Support/Microsoft/Teams/gpucache", "~/Library/Application Support/Microsoft/Teams/Local Storage", "~/Library/Application Support/Microsoft/Teams/tmp", "~/Library/Application Support/Microsoft/Teams/*logs*.txt", "~/Library/Application Support/Microsoft/Teams/watchdog", "~/Library/Application Support/Microsoft/Teams/*watchdog*.json"]},
    {"id": "java-heap-dumps", "title": "Java 堆转储", "tips": "~ 根下的 .hprof 文件", "risk": "recommend", "strategy": "delete", "depth": 1, "match": "*.hprof", "paths": ["~"]},
    {"id": "pyenv-venv-cache", "title": "Pyenv-VirtualEnv 缓存", "tips": "环境变量存在才生效", "risk": "recommend", "strategy": "delete", "paths": ["$PYENV_VIRTUALENV_CACHE_PATH"]}
  ],
  "command_rules": [
    {"id": "brew", "title": "Homebrew 清理", "tips": "brew cleanup -s 清缓存与旧版本", "command": ["brew", "cleanup", "-s"], "guard": "brew", "dry_paths": ["~/Library/Caches/Homebrew"]},
    {"id": "gem", "title": "旧版本 gem 清理", "tips": "gem cleanup", "command": ["gem", "cleanup"], "guard": "gem"},
    {"id": "docker", "title": "Docker 清理", "tips": "prune 掉未使用的镜像/容器/网络;需 Docker 正在运行", "command": ["docker", "system", "prune", "-af"], "guard": "docker", "risk": "caution"},
    {"id": "npm", "title": "npm 缓存清理", "tips": "npm cache clean", "command": ["npm", "cache", "clean", "--force"], "guard": "npm", "dry_paths": ["~/.npm"]},
    {"id": "yarn", "title": "yarn 缓存清理", "tips": "yarn cache clean", "command": ["yarn", "cache", "clean", "--force"], "guard": "yarn", "dry_paths": ["~/Library/Caches/yarn"]},
    {"id": "pnpm", "title": "pnpm store 清理", "tips": "pnpm store prune", "command": ["pnpm", "store", "prune"], "guard": "pnpm", "dry_paths": ["~/.pnpm-store"]},
    {"id": "pod", "title": "CocoaPods 缓存清理", "tips": "pod cache clean --all", "command": ["pod", "cache", "clean", "--all"], "guard": "pod", "dry_paths": ["~/Library/Caches/CocoaPods"]},
    {"id": "go", "title": "Go module 缓存清理", "tips": "go clean -modcache", "command": ["go", "clean", "-modcache"], "guard": "go", "dry_paths": ["~/go/pkg/mod"]},
    {"id": "conda", "title": "conda 缓存清理", "tips": "conda clean --all", "command": ["conda", "clean", "--all", "--yes"], "guard": "conda"},
    {"id": "composer", "title": "composer 缓存清理", "tips": "composer clear-cache", "command": ["composer", "clear-cache"], "guard": "composer", "dry_paths": ["~/Library/Caches/composer"]},
    {"id": "simctl", "title": "不可用模拟器清理", "tips": "xcrun simctl delete unavailable", "command": ["xcrun", "simctl", "delete", "unavailable"], "guard": "xcrun"}
  ],
  "aliases": {
    "com.youdao.note.YoudaoNoteMac": ["com.youdao.YoudaoDict"],
    "com.jetbrains.toolbox": ["Toolbox"]
  }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_rules_data -v`
Expected: 3 个测试全 PASS。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/rules.json tests/test_rules_data.py
git commit -m "feat: rules.json 规则库——Bash 清理块转译 + lemon 风险标记"
```

---

### Task 6: clean 执行器与 status

**Files:**
- Create: `cleanzd/clean.py`、`cleanzd/status.py`、`tests/test_clean.py`
- Modify: `cleanzd/__main__.py`(dispatch 接入 clean/status)

**Interfaces:**
- Consumes: `rules.load_rules/rule_targets`、`config.load_manifest/save_manifest`、`safety.safety_hit/validate_target/SafetyError`、`paths.*`
- Produces: `@dataclass CleanItem(source: str, path: Path, size: int, strategy: str, risk: str)`;`collect_items(include_caution=False, rules_path=None) -> tuple[list[CleanItem], list[CommandRule], list[str]]`(条目、可用命令规则、警告);`dispose(p: Path, purge: bool) -> None`(废纸篓优先,重名加后缀);`run_clean(dry_run, purge=False, include_caution=False, rules_path=None) -> dict`(report 含 dry_run/total_bytes/total_human/items/commands/warnings/freed_bytes/errors;真删后 strategy=delete 且路径已消失的 manifest 条目自动移除;历史追加进 `config_dir()/history.json`);`status.status_text() -> str`。

- [ ] **Step 1: 写失败测试**

`tests/test_clean.py`:

```python
from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from cleanzd import clean, config
from cleanzd.config import ManifestEntry

EMPTY_RULES = {"version": 1, "path_rules": [], "command_rules": [], "aliases": {}}

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
        self.assertEqual(config.load_manifest(), [])  # delete 条目清理后自动移除

    def test_empty_dir_keeps_dir_and_entry(self):
        victim = self.work / "cachedir"
        victim.mkdir()
        (victim / "f").write_bytes(b"x" * 10)
        config.manifest_add(ManifestEntry(path=str(victim), strategy="empty-dir"))
        clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        self.assertTrue(victim.exists())
        self.assertEqual(list(victim.iterdir()), [])
        self.assertEqual(len(config.load_manifest()), 1)  # empty-dir 条目长期保留

    def test_caution_skipped_by_default(self):
        victim = self.work / "risky"
        victim.mkdir()
        config.manifest_add(ManifestEntry(path=str(victim), strategy="delete", risk="caution"))
        report = clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        self.assertTrue(victim.exists())
        report2 = clean.run_clean(dry_run=False, purge=True, include_caution=True,
                                  rules_path=self.rules)
        self.assertFalse(victim.exists())

    def test_history_written(self):
        clean.run_clean(dry_run=False, purge=True, rules_path=self.rules)
        hist = json.loads((Path(self.cfg) / "history.json").read_text())
        self.assertEqual(len(hist), 1)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_clean -v`
Expected: `ModuleNotFoundError: No module named 'cleanzd.clean'`

- [ ] **Step 3: 实现 `cleanzd/clean.py`**

```python
from __future__ import annotations
import json, shutil, subprocess, time
from dataclasses import dataclass
from pathlib import Path
from .config import load_manifest, save_manifest
from .paths import config_dir, expand, human, path_size
from .rules import CommandRule, load_rules, rule_targets
from .safety import SafetyError, safety_hit, validate_target

@dataclass
class CleanItem:
    source: str     # "rule:<id>" 或 "manifest"
    path: Path
    size: int
    strategy: str   # 对该 path 的动作恒为 delete;empty-dir 已在收集时展开为子项
    risk: str

def collect_items(include_caution: bool = False, rules_path: Path | None = None):
    items: list[CleanItem] = []
    warnings: list[str] = []
    prules, crules, _ = load_rules(rules_path)
    for rule in prules:
        if rule.risk == "caution" and not include_caution:
            continue
        for t in rule_targets(rule):
            hit = safety_hit(t)
            if hit:
                warnings.append(f"[safety] 跳过 {t}(命中 {hit},规则 {rule.id})")
                continue
            items.append(CleanItem(f"rule:{rule.id}", t, path_size(t), "delete", rule.risk))
    for e in load_manifest():
        if e.risk == "caution" and not include_caution:
            continue
        p = expand(e.path)
        try:
            validate_target(p)
        except SafetyError as err:
            if p.exists() or p.is_symlink():
                warnings.append(f"[safety] 跳过清单条目 {e.path}: {err}")
            continue
        if e.strategy == "empty-dir" and p.is_dir():
            for child in sorted(p.iterdir()):
                items.append(CleanItem("manifest", child, path_size(child), "delete", e.risk))
        else:
            items.append(CleanItem("manifest", p, path_size(p), "delete", e.risk))
    usable_cmds = [c for c in crules
                   if shutil.which(c.guard) and (include_caution or c.risk != "caution")]
    return items, usable_cmds, warnings

def dispose(p: Path, purge: bool) -> None:
    if purge:
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        return
    trash = Path.home() / ".Trash"
    dest = trash / p.name
    n = 1
    while dest.exists() or dest.is_symlink():
        dest = trash / f"{p.name}.cleanzd-{int(time.time())}-{n}"
        n += 1
    shutil.move(str(p), str(dest))

def run_clean(dry_run: bool, purge: bool = False, include_caution: bool = False,
              rules_path: Path | None = None) -> dict:
    items, cmds, warnings = collect_items(include_caution, rules_path)
    total = sum(i.size for i in items)
    report = {"dry_run": dry_run, "total_bytes": total, "items": len(items),
              "commands": [c.id for c in cmds], "warnings": warnings,
              "freed_bytes": 0, "errors": []}
    if dry_run:
        for c in cmds:
            report["total_bytes"] += sum(path_size(expand(d)) for d in c.dry_paths)
        report["total_human"] = human(report["total_bytes"])
        return report
    freed = 0
    for item in items:
        try:
            dispose(item.path, purge)
            freed += item.size
        except OSError as err:
            report["errors"].append(f"{item.path}: {err}")
    for c in cmds:
        try:
            subprocess.run(c.command, check=False, capture_output=True, timeout=1800)
        except (subprocess.SubprocessError, OSError) as err:
            report["errors"].append(f"{c.id}: {err}")
    entries = load_manifest()
    kept = [e for e in entries
            if not (e.strategy == "delete" and not expand(e.path).exists())]
    if len(kept) != len(entries):
        save_manifest(kept)
    report["freed_bytes"] = freed
    report["freed_human"] = human(freed)
    report["total_human"] = human(total)
    _append_history(report)
    return report

def _append_history(report: dict) -> None:
    f = config_dir() / "history.json"
    hist = json.loads(f.read_text()) if f.exists() else []
    hist.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "freed_bytes": report["freed_bytes"],
                 "items": report["items"], "errors": len(report["errors"])})
    f.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n")
```

`cleanzd/status.py`:

```python
from __future__ import annotations
import json
from .config import load_ignore, load_manifest
from .paths import config_dir, human

def status_text() -> str:
    manifest = load_manifest()
    ignore = load_ignore()
    ed = sum(1 for e in manifest if e.strategy == "empty-dir")
    lines = [f"清单条目: {len(manifest)}(empty-dir {ed} / delete {len(manifest) - ed})",
             f"忽略名单: {len(ignore)}"]
    f = config_dir() / "history.json"
    if f.exists():
        hist = json.loads(f.read_text())
        if hist:
            last = hist[-1]
            lines.append(f"上次清理: {last['time']},释放 {human(last['freed_bytes'])}")
            lines.append(f"累计清理 {len(hist)} 次,共释放 "
                         f"{human(sum(h['freed_bytes'] for h in hist))}")
    return "\n".join(lines)
```

`cleanzd/__main__.py` 的 `main()` 替换为:

```python
def main(argv=None) -> int:
    import json as _json
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        from .status import status_text
        print(status_text())
        return 0
    if args.cmd == "clean":
        from .clean import run_clean
        from .paths import human
        report = run_clean(dry_run=args.dry_run, purge=args.purge,
                           include_caution=args.include_caution)
        if args.json:
            print(_json.dumps(report, ensure_ascii=False, indent=2, default=str))
        else:
            for w in report["warnings"]:
                print(w, file=sys.stderr)
            if report["dry_run"]:
                print(f"[dry-run] 可清理 {report['items']} 项,预计释放 {report['total_human']};"
                      f"另有命令规则: {', '.join(report['commands']) or '无'}")
            else:
                print(f"已清理 {report['items']} 项,释放 {report['freed_human']};"
                      f"错误 {len(report['errors'])} 个")
                for e in report["errors"]:
                    print(f"  ! {e}", file=sys.stderr)
        return 0
    print(f"子命令 {args.cmd} 尚未实现", file=sys.stderr)
    return 1
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest tests.test_clean tests.test_cli -v`
Expected: 全 PASS。再手工 `./clean-zd clean --dry-run` 真跑一次(用真实 rules.json,只读)确认输出统计合理、无 traceback。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/clean.py cleanzd/status.py cleanzd/__main__.py tests/test_clean.py
git commit -m "feat: clean 执行器(dry-run/废纸篓/命令规则/历史)与 status"
```

---

### Task 7: scan 编排、渲染与 manifest 子命令接线

**Files:**
- Create: `cleanzd/scan/__init__.py`、`tests/test_scan.py`
- Modify: `cleanzd/__main__.py`(接入 scan 与 manifest 子命令)

**Interfaces:**
- Consumes: `config.decided_paths`、`safety.safety_hit`、`rules.load_rules`、`paths.human`
- Produces: `@dataclass Candidate(path: str, category: str, size: int, evidence: str, risk: str, suggested_strategy: str)`;`rule_covered(rules_path=None) -> set[str]`(所有 path 规则 base 展开集合);`run_scan(categories=None, threshold_mb=500, dirs=None, rules_path=None) -> list[Candidate]`(调各扫描器→过滤 decided/safety/rule_covered→按体积降序);`render_table(cands) -> str`;`render_json(cands) -> str`。各具体扫描器(Task 8/9)统一暴露 `scan() -> list[Candidate]`(bigfile 为 `scan(threshold_mb, dirs)`)。本任务先建占位扫描器模块(空列表),Task 8/9 填充。

- [ ] **Step 1: 写失败测试**

`tests/test_scan.py`:

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_scan -v`
Expected: ImportError。

- [ ] **Step 3: 实现 `cleanzd/scan/__init__.py` 与四个占位扫描器**

```python
from __future__ import annotations
import glob as _glob
import json as _json
from dataclasses import asdict, dataclass
from pathlib import Path
from ..config import decided_paths
from ..paths import expand, human
from ..rules import load_rules
from ..safety import safety_hit

@dataclass
class Candidate:
    path: str
    category: str            # cache|dev|leftover|bigfile|system
    size: int
    evidence: str
    risk: str                # recommend | caution
    suggested_strategy: str  # empty-dir | delete

def rule_covered(rules_path=None) -> set[str]:
    covered: set[str] = set()
    prules, _crules, _ = load_rules(rules_path)
    for r in prules:
        for raw in r.paths:
            s = str(expand(raw))
            if any(ch in s for ch in "*?["):
                covered.update(_glob.glob(s))
            else:
                covered.add(s)
    return covered

def _admit(cands: list[Candidate], seen: set[str]) -> list[Candidate]:
    out = []
    for c in cands:
        if c.path in seen or safety_hit(Path(c.path)):
            continue
        seen.add(c.path)
        out.append(c)
    return out

def run_scan(categories=None, threshold_mb: int = 500, dirs=None,
             rules_path=None) -> list[Candidate]:
    from . import bigfile, cache, dev, leftover, systemitems
    cats = categories if categories is not None else \
        ["cache", "dev", "leftover", "bigfile", "system"]
    seen = set(decided_paths()) | rule_covered(rules_path)
    out: list[Candidate] = []
    if "cache" in cats:
        out += _admit(cache.scan(), seen)
    if "dev" in cats:
        out += _admit(dev.scan(), seen)
    if "leftover" in cats:
        out += _admit(leftover.scan(), seen)
    if "bigfile" in cats:
        out += _admit(bigfile.scan(threshold_mb, dirs), seen)
    if "system" in cats:
        out += _admit(systemitems.scan(), seen)
    out.sort(key=lambda c: c.size, reverse=True)
    return out

def render_json(cands: list[Candidate]) -> str:
    return _json.dumps([asdict(c) for c in cands], ensure_ascii=False, indent=2)

def render_table(cands: list[Candidate]) -> str:
    lines = [f"{'体积':>10}  {'类别':<8} {'风险':<9} 路径"]
    for c in cands:
        lines.append(f"{human(c.size):>10}  {c.category:<8} {c.risk:<9} {c.path}")
        if c.evidence:
            lines.append(f"{'':>10}  {'':<8} {'':<9} └ {c.evidence}")
    return "\n".join(lines)
```

四个占位模块 `cleanzd/scan/{cache,dev,leftover,systemitems}.py`(内容一致,Task 8/9 替换):

```python
from __future__ import annotations
from . import Candidate

def scan() -> list[Candidate]:
    return []
```

`cleanzd/scan/bigfile.py` 占位:

```python
from __future__ import annotations
from . import Candidate

def scan(threshold_mb: int = 500, dirs=None) -> list[Candidate]:
    return []
```

`__main__.py` 的 `main()` 中在 `if args.cmd == "status"` 前插入:

```python
    if args.cmd == "scan":
        from .scan import render_json, render_table, run_scan
        cands = run_scan(categories=args.category, threshold_mb=args.threshold_mb,
                         dirs=args.dir)
        print(render_json(cands) if args.json else
              (render_table(cands) if cands else "没有新的候选清理项"))
        return 0
    if args.cmd == "manifest":
        from .config import (ManifestEntry, ignore_add, load_ignore, load_manifest,
                             manifest_add, manifest_remove)
        from .safety import SafetyError
        if args.mcmd == "add":
            try:
                manifest_add(ManifestEntry(path=args.path, strategy=args.strategy,
                                           risk=args.risk, type=args.type,
                                           reason=args.reason, decided_by=args.decided_by))
            except SafetyError as err:
                print(f"拒绝写入: {err}", file=sys.stderr)
                return 1
            print(f"已登记: {args.path}")
            return 0
        if args.mcmd == "remove":
            ok = manifest_remove(args.path)
            print("已移除" if ok else "清单中不存在该条目")
            return 0 if ok else 1
        if args.mcmd == "ignore":
            ignore_add(args.path, args.reason, args.decided_by)
            print(f"已加入忽略名单: {args.path}")
            return 0
        if args.mcmd == "list":
            import dataclasses
            data = {"manifest": [dataclasses.asdict(e) for e in load_manifest()],
                    "ignore": load_ignore()}
            if args.json:
                print(_json.dumps(data, ensure_ascii=False, indent=2))
            else:
                for e in data["manifest"]:
                    print(f"[清单] {e['path']}  {e['strategy']}/{e['risk']}  "
                          f"by {e['decided_by']}  {e['reason']}")
                for i in data["ignore"]:
                    print(f"[忽略] {i['path']}  {i['reason']}")
            return 0
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m unittest discover -s tests -v`
Expected: 全 PASS。手工验证:`./clean-zd scan`(此时输出「没有新的候选清理项」)、`./clean-zd manifest list`。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/scan/ cleanzd/__main__.py tests/test_scan.py
git commit -m "feat: scan 编排/渲染/过滤与 manifest 子命令接线"
```

---

### Task 8: cache / system / bigfile 三个扫描器

**Files:**
- Modify: `cleanzd/scan/cache.py`、`cleanzd/scan/systemitems.py`、`cleanzd/scan/bigfile.py`(替换占位)
- Test: `tests/test_scan.py`(追加)

**Interfaces:**
- Consumes: `Candidate`、`paths.expand/path_size`
- Produces: `cache.scan() -> list[Candidate]`(来源:`~/Library/Caches/*`、`~/Library/Logs/*`、`~/Library/Application Support/*/Cache{,s}`、`~/Library/Containers/*/Data/Library/Caches`、`getconf DARWIN_USER_CACHE_DIR` 子目录;<1MB 忽略;`_scan_roots(roots)` 拆出便于测试);`systemitems.scan()`(废纸篓/Mail Downloads/iOS 备份,一律 caution);`bigfile.scan(threshold_mb, dirs)`(默认 `~/Downloads`+`~/Desktop` 一层,超阈值文件/目录,caution,证据含最后修改天数;`_scan(roots, thr)` 拆出便于测试)。

- [ ] **Step 1: 追加失败测试到 `tests/test_scan.py`**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_scan -v`
Expected: `AttributeError`(`_scan_roots`/`_scan` 不存在)。

- [ ] **Step 3: 实现三个扫描器**

`cleanzd/scan/cache.py`:

```python
from __future__ import annotations
import glob, subprocess
from pathlib import Path
from ..paths import expand, path_size
from . import Candidate

MIN_SIZE = 1024 * 1024  # 1MB 以下不报,压噪音

def _scan_roots(roots: list[str], evidence: str) -> list[Candidate]:
    out: list[Candidate] = []
    for root in roots:
        base = Path(root)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            size = path_size(child)
            if size >= MIN_SIZE:
                out.append(Candidate(str(child), "cache", size, evidence,
                                     "recommend", "empty-dir"))
    return out

def _darwin_cache_dir() -> str | None:
    try:
        r = subprocess.run(["getconf", "DARWIN_USER_CACHE_DIR"],
                           capture_output=True, text=True, timeout=10)
        p = r.stdout.strip()
        return p if p and Path(p).is_dir() else None
    except (subprocess.SubprocessError, OSError):
        return None

def scan() -> list[Candidate]:
    out = _scan_roots([str(expand("~/Library/Caches"))], "~/Library/Caches 下缓存目录")
    out += _scan_roots([str(expand("~/Library/Logs"))], "~/Library/Logs 下日志目录")
    as_caches = glob.glob(str(expand("~/Library/Application Support/*/Cache"))) + \
        glob.glob(str(expand("~/Library/Application Support/*/Caches")))
    for d in sorted(as_caches):
        size = path_size(Path(d))
        if size >= MIN_SIZE:
            out.append(Candidate(d, "cache", size,
                                 "Application Support 内 Cache 目录", "recommend", "empty-dir"))
    for d in sorted(glob.glob(str(expand("~/Library/Containers/*/Data/Library/Caches")))):
        size = path_size(Path(d))
        if size >= MIN_SIZE:
            out.append(Candidate(d, "cache", size, "沙盒容器内缓存(lemon appstore 规则同源)",
                                 "recommend", "empty-dir"))
    dud = _darwin_cache_dir()
    if dud:
        out += _scan_roots([dud], "darwin per-app 临时缓存(SystemTempDir)")
    return out
```

`cleanzd/scan/systemitems.py`:

```python
from __future__ import annotations
from ..paths import expand, path_size
from . import Candidate

ITEMS = (
    ("~/.Trash", "废纸篓(清空前确认)"),
    ("~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads", "Mail 附件缓存"),
    ("~/Library/Application Support/MobileSync/Backup", "iOS 设备备份(确认已另有备份)"),
)

def scan() -> list[Candidate]:
    out = []
    for raw, title in ITEMS:
        p = expand(raw)
        if p.is_dir():
            size = path_size(p)
            if size >= 1024 * 1024:
                out.append(Candidate(str(p), "system", size, title, "caution", "empty-dir"))
    return out
```

`cleanzd/scan/bigfile.py`:

```python
from __future__ import annotations
import time
from pathlib import Path
from ..paths import expand, path_size
from . import Candidate

DEFAULT_DIRS = ("~/Downloads", "~/Desktop")

def _scan(roots: list[str], thr: int) -> list[Candidate]:
    out: list[Candidate] = []
    for root in roots:
        base = Path(root)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            size = path_size(child)
            if size < thr:
                continue
            try:
                days = int((time.time() - child.lstat().st_mtime) // 86400)
            except OSError:
                days = -1
            out.append(Candidate(str(child), "bigfile", size,
                                 f"超过阈值,最后修改 {days} 天前", "caution", "delete"))
    return out

def scan(threshold_mb: int = 500, dirs=None) -> list[Candidate]:
    roots = [str(expand(d)) for d in (dirs or DEFAULT_DIRS)]
    return _scan(roots, threshold_mb * 1024 * 1024)
```

- [ ] **Step 4: 跑测试确认通过 + 真跑**

Run: `python3 -m unittest discover -s tests -v` → 全 PASS。
Run: `./clean-zd scan --category cache --category system --category bigfile`(只读安全)→ 人工检查输出:候选合理、安全名单目录(如 com.apple.dock)不出现、体积降序。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/scan/ tests/test_scan.py
git commit -m "feat: cache/system/bigfile 扫描器(含沙盒容器与 SystemTempDir 盲区)"
```

---

### Task 9: dev 与 leftover 扫描器

**Files:**
- Modify: `cleanzd/scan/dev.py`、`cleanzd/scan/leftover.py`(替换占位)
- Test: `tests/test_leftover.py`

**Interfaces:**
- Consumes: `Candidate`、`rules.load_rules`(取 aliases)、`plistlib`
- Produces: `dev.scan()`(固定已知开发产物位置清单,≥50MB 才报);`leftover.scan()`;`leftover.installed_identities() -> tuple[set[str], set[str]]`(bundleIDs、names 小写);`leftover.vendor_prefixes(bundles) -> set[str]`(取 bundleID 前两段);`leftover.is_orphan(dirname: str, bundles: set, names: set, vendors: set, owned: set) -> str | None`(孤儿返回证据文案,否则 None;**仅对形似 bundle id(≥2 个点)的目录名判定**,厂商前缀命中/名称双向前缀命中/排除名单命中一律放行)。

- [ ] **Step 1: 写失败测试**

`tests/test_leftover.py`:

```python
from __future__ import annotations
import unittest
from cleanzd.scan.leftover import is_orphan, vendor_prefixes

BUNDLES = {"com.tencent.xinWeChat", "com.apple.dt.Xcode", "com.jetbrains.intellij"}
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
        # 装着微信 → com.tencent.* 一律不判孤儿(lemon 厂商前缀保护)
        self.assertIsNone(self.check("com.tencent.QQMusicMac"))

    def test_apple_excluded(self):
        self.assertIsNone(self.check("com.apple.gone.app.cache"))

    def test_orphan_detected(self):
        self.assertIsNotNone(self.check("com.sketchup.SketchUp.2021"))

    def test_non_bundle_name_skipped(self):
        # 不形似 bundle id 的目录名保守放行
        self.assertIsNone(self.check("SomeRandomFolder"))

    def test_alias_owned(self):
        self.assertIsNone(is_orphan("com.youdao.YoudaoDict", BUNDLES, NAMES, VENDORS,
                                    {"com.youdao.YoudaoDict"}))

    def test_name_prefix_match(self):
        self.assertIsNone(self.check("com.jetbrains.intellij.idea.backend"))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m unittest tests.test_leftover -v`
Expected: ImportError(`is_orphan` 不存在)。

- [ ] **Step 3: 实现**

`cleanzd/scan/dev.py`:

```python
from __future__ import annotations
from ..paths import expand, path_size
from . import Candidate

MIN_SIZE = 50 * 1024 * 1024
KNOWN = (
    ("~/Library/Developer/Xcode/iOS DeviceSupport", "caution", "旧设备调试符号,连新设备会重建"),
    ("~/Library/Developer/Xcode/macOS DeviceSupport", "caution", "旧设备调试符号"),
    ("~/Library/Developer/CoreSimulator/Caches", "recommend", "模拟器缓存"),
    ("~/Library/Caches/pip", "recommend", "pip 下载缓存"),
    ("~/.cargo/registry/cache", "recommend", "Rust registry 下载缓存"),
    ("~/.m2/repository", "caution", "Maven 本地仓库,重下耗时"),
    ("~/.docker", "caution", "Docker 数据根,建议用 docker system prune 处理"),
)

def scan() -> list[Candidate]:
    out = []
    for raw, risk, why in KNOWN:
        p = expand(raw)
        if p.exists():
            size = path_size(p)
            if size >= MIN_SIZE:
                out.append(Candidate(str(p), "dev", size, why, risk, "empty-dir"))
    return out
```

`cleanzd/scan/leftover.py`:

```python
from __future__ import annotations
import plistlib
from pathlib import Path
from ..paths import expand, path_size
from ..rules import load_rules
from . import Candidate

SEARCH_DIRS = (
    "~/Library/Application Support", "~/Library/Caches", "~/Library/Preferences",
    "~/Library/Saved Application State", "~/Library/Logs", "~/Library/Containers",
    "~/Library/LaunchAgents", "~/Library/WebKit", "~/Library/HTTPStorages",
)
# 出处: docs/reference/lemon-cleaner-knowledge.md §1.4
EXCLUDE_PREFIXES = ("com.apple", "com.microsoft", "loginwindow", "usereventagent",
                    "com.hex-rays.ida")
MIN_SIZE = 10 * 1024 * 1024

def installed_identities() -> tuple[set[str], set[str]]:
    bundles: set[str] = set()
    names: set[str] = set()
    for appdir in ("/Applications", str(Path.home() / "Applications")):
        base = Path(appdir)
        if not base.is_dir():
            continue
        for app in sorted(base.glob("*.app")):
            names.add(app.stem.lower())
            try:
                with open(app / "Contents" / "Info.plist", "rb") as fh:
                    info = plistlib.load(fh)
            except (OSError, plistlib.InvalidFileException):
                continue
            if info.get("CFBundleIdentifier"):
                bundles.add(str(info["CFBundleIdentifier"]))
            for key in ("CFBundleName", "CFBundleExecutable"):
                if info.get(key):
                    names.add(str(info[key]).lower())
    return bundles, names

def vendor_prefixes(bundles: set[str]) -> set[str]:
    return {".".join(b.split(".")[:2]).lower() for b in bundles if "." in b}

def is_orphan(dirname: str, bundles: set[str], names: set[str],
              vendors: set[str], owned: set[str]) -> str | None:
    low = dirname.lower()
    if dirname in owned:
        return None
    for pref in EXCLUDE_PREFIXES:
        if low.startswith(pref):
            return None
    if "steam" in low:
        return None
    if low.count(".") < 2:
        return None  # 不形似 bundle id,保守放行
    for b in bundles:
        bl = b.lower()
        if low == bl or low.startswith(bl + ".") or bl.startswith(low + "."):
            return None
    for v in vendors:
        if low.startswith(v + "."):
            return None  # 厂商前缀保护
    for n in names:
        if n and (low.startswith(n) or n.startswith(low)):
            return None
    return "形似 bundle id 且在已装应用中找不到对应(卸载残留候选)"

def scan() -> list[Candidate]:
    bundles, names = installed_identities()
    vendors = vendor_prefixes(bundles)
    _p, _c, aliases = load_rules()
    owned: set[str] = set()
    for bid, dirnames in aliases.items():
        if bid in bundles:
            owned.update(dirnames)
    out: list[Candidate] = []
    for raw in SEARCH_DIRS:
        base = expand(raw)
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            evidence = is_orphan(child.name, bundles, names, vendors, owned)
            if not evidence:
                continue
            size = path_size(child)
            if size >= MIN_SIZE:
                out.append(Candidate(str(child), "leftover", size,
                                     f"{evidence};位于 {raw}", "caution", "delete"))
    return out
```

- [ ] **Step 4: 跑测试确认通过 + 真跑**

Run: `python3 -m unittest discover -s tests -v` → 全 PASS。
Run: `./clean-zd scan --category leftover --category dev` → 人工抽查:已装应用(微信等)不出现在 leftover;出现的孤儿候选人工核对 2-3 个确属已卸载软件。

- [ ] **Step 5: Commit**

```bash
git add cleanzd/scan/dev.py cleanzd/scan/leftover.py tests/test_leftover.py
git commit -m "feat: dev/leftover 扫描器(身份四元组+厂商前缀保护+别名)"
```

---

### Task 10: Bash 对比验证、退役与文档切换

**Files:**
- Delete: `legacy/clean-zd.bash`、`installer.sh`、`.github/workflows/release.yml`
- Modify: `README.md`、`AGENTS.md`
- Create: `docs/dev-log/2026-07-18-v2-python-rewrite.md`

**Interfaces:** 无代码接口;交付「转译无遗漏」的证据与文档一致性。

- [ ] **Step 1: 对比验证**

```bash
bash legacy/clean-zd.bash -d 2>&1 | tee /tmp/bash-dry.txt   # 会提示 sudo 密码,dry-run 非破坏;结束在 Continue? 提示处 Ctrl-C
./clean-zd clean --dry-run --include-caution --json > /tmp/py-dry.json
```

逐块核对:bash 输出的每条 `msg` 对应的路径集,在 `py-dry.json` 的 items/commands 中能找到对应规则,或出现在下方「有意放弃」清单中。**有意放弃清单**(写入 dev-log):`/Volumes/*/.Trashes`、`/Library/Caches`、`/System/Library/Caches`、`/private/var/folders/bh` 裸 glob、`/private/var/log/asl`、`/Library/Logs/*`(DiagnosticReports/CreativeCloud/Adobe)、DNS flush、`sudo purge`、`brew -u` 更新流程、docker 自动启停(以上均需 root/sudo 或属升级而非清理;v2 只做用户态清理)。发现真正遗漏则回 Task 5 补规则后重验。

- [ ] **Step 2: 退役与文档**

```bash
git rm legacy/clean-zd.bash installer.sh .github/workflows/release.yml
```

改写 `README.md`:定位一句话(AI 驱动的 Mac 清理助手引擎)、安装(`git clone` 后 `ln -s "$PWD/clean-zd" /usr/local/bin/clean-zd`,或直接 `./clean-zd`)、四个子命令示例、与 skill 配合的说明、致谢保留 mac-cleanup-sh 与 lemon-cleaner。
改写 `AGENTS.md`:替换「What this is / Running & testing / Architecture」为 Python 三层架构描述(目录结构、`python3 -m unittest discover -s tests`、dry-run 约定、safety 铁律、rules.json schema 摘要);保留 dev-log 约定;删除 Homebrew release 段。

- [ ] **Step 3: 写 dev-log**

`docs/dev-log/2026-07-18-v2-python-rewrite.md`:背景/目标(v2 规格链接)、改动内容(三层架构、模块清单、规则转译对照、有意放弃清单及理由)、验证方式(unittest 数、dry-run 对比结论)、遗留/后续(规格「后续迭代」章节 + skill 任务)、相关提交。

- [ ] **Step 4: 全量回归**

Run: `python3 -m unittest discover -s tests -v` → 全 PASS;`./clean-zd status`、`./clean-zd scan`、`./clean-zd clean --dry-run` 各真跑一次无 traceback。

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat!: Bash 退役,clean-zd 全面切换 Python v2(含 dry-run 对比验证与文档)"
```

---

### Task 11: market-zd skill 薄壳(zd-mac-clean)

**Files:**(在 `~/github/market-zd` 仓库)
- Create: `plugins/zd-mac-clean/.claude-plugin/plugin.json`、`plugins/zd-mac-clean/skills/mac-clean/SKILL.md`
- 注意:先 `ls ~/github/market-zd/plugins/` 查看现有插件(如 zd-multi-ai)的实际清单文件结构与字段,保持一致;若清单文件名/位置约定不同,以仓库现状为准。

**Interfaces:**
- Consumes: 引擎 CLI 全部子命令(`clean-zd scan --json` / `manifest add|ignore|list` / `clean --dry-run` / `clean` / `status`)。
- Produces: 用户在 Claude Code 说「清理电脑/清理磁盘/mac clean」时触发的 skill。

- [ ] **Step 1: plugin.json**

```json
{
  "name": "zd-mac-clean",
  "version": "0.1.0",
  "description": "AI 驱动的 Mac 清理助手:驱动 clean-zd 引擎扫描-判断-记录-清理"
}
```

- [ ] **Step 2: SKILL.md**

```markdown
---
name: mac-clean
description: AI 驱动的 Mac 清理助手。触发:清理电脑、清理磁盘、释放空间、mac 清理、clean my mac。驱动本机 clean-zd 引擎完成扫描→逐项判断→存疑问用户→记录清单→dry-run 确认→清理的完整闭环;AI 永不直接删除文件,一切删除经引擎的安全校验与废纸篓机制。
---

# mac-clean:AI 驱动的 Mac 清理助手

## 前置检查

1. `command -v clean-zd || ls ~/github/mac-cleanup/clean-zd` 找到引擎;找不到则告知用户安装(git clone shake863/mac-cleanup 并符号链接),本次终止。
2. `clean-zd status` 了解清单现状,向用户简报。

## 铁律(违反即事故)

- **你永远不执行 rm/rmdir/shutil 删除,也不让用户执行**。一切删除只通过 `clean-zd clean`。
- 你的判断只通过 `clean-zd manifest add / ignore` 落地,引擎会做安全校验;校验拒绝就接受拒绝,把原因告诉用户,绝不绕过。
- `risk=caution` 的候选与"删除类"(不可再生文件,如大文件、备份、残留)必须问用户,不得自作主张。
- 缓存/日志类(可再生)你可自主判断,但必须给出理由(reason 写入清单)。

## 工作流

1. **扫描**:`clean-zd scan --json`(耗时可能数分钟)。候选为空 → 直接跳到第 5 步。
2. **逐项判断**:对每个候选,依据 path/category/evidence/risk 判断:
   - 认识且确定可清(如已知 app 缓存)→ `clean-zd manifest add <path> --strategy <empty-dir|delete> --reason "<为什么可清>" --decided-by ai`;
   - 认识且确定不该清 → `clean-zd manifest ignore <path> --reason "<为什么>" --decided-by ai`;
   - 拿不准 / risk=caution / 删除不可再生数据 → 收集起来交下一步。
3. **问用户**:用 AskUserQuestion 分批询问存疑项,每项给出:路径、体积、证据、你的倾向与理由。按用户决定写入 manifest(--decided-by user)或 ignore。
4. **记录沉淀提示**:若某条判断具有普适性(不依赖本机特有软件组合),提示用户可将其提交为 mac-cleanup 仓库 rules.json 的规则。
5. **dry-run**:`clean-zd clean --dry-run` 向用户展示将清理的项数与预计释放空间(若用户明确要清 caution 项,加 --include-caution)。
6. **确认后执行**:用户确认后 `clean-zd clean`(默认进废纸篓;用户明确要求才加 --purge)。展示释放空间与错误。
7. **收尾**:`clean-zd status` 简报;提醒用户下次直接说"清理电脑"即可复用清单秒清。

## 判断准则

- 可再生(缓存/日志/索引):可自主判断为可清。
- 不可再生(文档、安装包可能还要用、备份、残留里可能有数据):必问用户。
- 完全不认识的路径:宁可 ignore 或问用户,不猜。
- 体积小(<50MB)且不确定:建议 ignore,压低后续噪音。
```

- [ ] **Step 3: 验证**

在 mac-cleanup 已完成 Task 1-10 的前提下,于 Claude Code 中真实走一遍:「清理电脑」→ 触发 skill → 扫描 → 判断/问询 → dry-run → 清理 → status。确认 AI 全程未直接执行删除命令、清单条目 reason/decided_by 填写正确。

- [ ] **Step 4: Commit(market-zd 仓库)**

```bash
cd ~/github/market-zd && git add plugins/zd-mac-clean && git commit -m "feat: zd-mac-clean 插件——AI 驱动 Mac 清理助手 skill 薄壳"
```

---

## Self-Review 记录

- **规格覆盖**:三层架构(T1-T9 执行层、T5 知识层、T11 智能层)、五类扫描(T8 cache/system/bigfile、T9 dev/leftover)、安全铁律(T2/T6)、沙盒容器与 SystemTempDir 盲区(T8)、残留匹配算法(T9)、Bash 退役与 dry-run 对比(T10)、沉淀闭环(T11 SKILL.md 第 4 步)。规格「后续迭代」章节(node_modules/体积缓存/pkgutil 完整清单)明确不在本计划。
- **有意偏离规格处**(已在任务内注明):需 root 的旧 Bash 块放弃(T10 清单);`manifest ignore` 作为 manifest 子命令而非独立文件操作;命令规则增加 `dry_paths` 字段以支撑 dry-run 统计。
- **类型一致性**:`Candidate`/`ManifestEntry`/`PathRule`/`CommandRule` 字段与各消费方(T6-T9、T11 SKILL.md 的 CLI 参数)已互查一致;`run_clean(rules_path=...)` 测试注入点在 T6 定义、T6 测试使用。
```
