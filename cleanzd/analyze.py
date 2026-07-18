from __future__ import annotations

import json as _json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import expand, human, path_size


class AnalyzeError(Exception):
    """analyze 目标未通过校验或不可读。"""


@dataclass(frozen=True)
class Signature:
    name: str
    rebuildable: bool
    hint: str
    anchor: str  # 兄弟 marker 文件名,作为项目活跃度锚点;空串表示用自身 mtime


# 签名判定必须带上下文锚(兄弟 marker),防止误伤同名的普通目录。
# 需求出处见 docs/dev-log/2026-07-19-analyze-disk-usage.md
_GRADLE_MARKERS = ("build.gradle", "build.gradle.kts")
_JS_BUILD_NAMES = {"dist", "build", ".next", "out"}
_VENV_NAMES = {".venv", "venv", "env"}
PROJECT_MARKERS = (
    ".git",
    "package.json",
    "Cargo.toml",
    "pyproject.toml",
    "go.mod",
) + _GRADLE_MARKERS
USER_DATA_DIRS = {"Documents", "Desktop", "Downloads", "Pictures", "Movies", "Music"}


def detect_signature(path: Path) -> Signature | None:
    if not path.is_dir():
        return None
    parent = path.parent
    name = path.name
    if name == "node_modules" and (parent / "package.json").exists():
        return Signature(
            "node_modules", True, "npm 依赖目录,可由 npm install 重建", "package.json"
        )
    if name == "target" and (parent / "Cargo.toml").exists():
        return Signature("cargo-target", True, "Rust 编译产物,cargo clean 可清", "Cargo.toml")
    for marker in _GRADLE_MARKERS:
        if name == "build" and (parent / marker).exists():
            return Signature("gradle-build", True, "Gradle 构建产物,gradle clean 可清", marker)
    if name in _JS_BUILD_NAMES and (parent / "package.json").exists():
        return Signature("js-build", True, "前端构建产物,重新构建即可生成", "package.json")
    if (path / "pyvenv.cfg").exists() or (
        name in _VENV_NAMES and (path / "bin" / "python").exists()
    ):
        return Signature("python-venv", True, "Python 虚拟环境,可删后重建", "")
    if parent.name == "envs" and "conda" in parent.parent.name.lower():
        return Signature("conda-env", True, "conda 环境,conda env remove 可移除", "")
    return None


def classify_kind(path: Path, home: Path) -> str:
    if path.is_dir():
        for marker in PROJECT_MARKERS:
            if (path / marker).exists():
                return "dev-project"
    try:
        rel = path.resolve().relative_to(home.resolve())
    except ValueError:
        return "unknown"
    parts = rel.parts
    if not parts:
        return "unknown"
    if parts[0] == "Library":
        if len(parts) > 1 and parts[1] == "Caches":
            return "cache"
        return "app-data"
    if parts[0] in USER_DATA_DIRS:
        return "user-data"
    return "unknown"


def _age_days(path: Path, signature: Signature | None) -> int:
    candidates = [path]
    if signature is not None and signature.anchor:
        git_head = path.parent / ".git" / "HEAD"
        anchor = path.parent / signature.anchor
        candidates = [p for p in (git_head, anchor) if p.exists()] or [path]
    else:
        own_head = path / ".git" / "HEAD"
        if own_head.exists():
            candidates = [own_head]
    newest = 0.0
    for candidate in candidates:
        try:
            newest = max(newest, candidate.lstat().st_mtime)
        except OSError:
            pass
    if newest <= 0:
        return 0
    return max(0, int((time.time() - newest) / 86400))


_KIND_HINTS = {
    "dev-project": "开发项目,勿整体删除;可下探其内部产物",
    "cache": "缓存目录,可下探或走 scan 流程",
    "user-data": "用户数据,默认有价值,勿动",
}


@dataclass
class Item:
    path: str
    size: int
    size_human: str
    percent: float
    kind: str
    signature: str
    rebuildable: bool
    age_days: int
    hint: str


def run_analyze(
    raw_dir: str,
    top: int = 20,
    min_size_mb: int = 10,
    home: Path | None = None,
) -> dict:
    home = (home or Path.home()).resolve()
    raw = expand(raw_dir)
    if not raw.exists():
        raise AnalyzeError(f"路径不存在: {raw}")
    resolved = raw.resolve()
    if not resolved.is_dir():
        raise AnalyzeError(f"不是目录: {raw}")
    if resolved != home and not resolved.is_relative_to(home):
        raise AnalyzeError(f"路径不在家目录内(或经软链逃逸): {raw} -> {resolved}")
    try:
        children = list(resolved.iterdir())
    except OSError as err:
        raise AnalyzeError(f"无权限读取目录: {resolved}") from err

    items: list[Item] = []
    total = 0
    for child in children:
        size = path_size(child)
        total += size
        signature = detect_signature(child)
        kind = "dev-artifact" if signature else classify_kind(child, home)
        items.append(
            Item(
                path=str(child),
                size=size,
                size_human=human(size),
                percent=0.0,
                kind=kind,
                signature=signature.name if signature else "",
                rebuildable=bool(signature and signature.rebuildable),
                age_days=_age_days(child, signature),
                hint=signature.hint if signature else _KIND_HINTS.get(kind, ""),
            )
        )
    for item in items:
        item.percent = round(item.size * 100.0 / total, 1) if total else 0.0
    items.sort(key=lambda i: i.size, reverse=True)

    min_bytes = min_size_mb * 1024 * 1024
    kept = [i for i in items if i.size >= min_bytes][:top]
    omitted = [i for i in items if i not in kept]
    return {
        "dir": str(resolved),
        "total": total,
        "total_human": human(total),
        "items": [asdict(i) for i in kept],
        "omitted": {
            "count": len(omitted),
            "size": sum(i.size for i in omitted),
            "size_human": human(sum(i.size for i in omitted)),
        },
    }


def render_json(report: dict) -> str:
    return _json.dumps(report, ensure_ascii=False, indent=2)


def render_table(report: dict) -> str:
    lines = [f"分析目录: {report['dir']}(共 {report['total_human']})"]
    lines.append(f"{'体积':>10} {'占比':>6}  {'定性':<12} {'年龄':>6}  路径")
    for item in report["items"]:
        lines.append(
            f"{item['size_human']:>10} {item['percent']:>5.1f}%  "
            f"{item['kind']:<12} {item['age_days']:>4}天  {item['path']}"
        )
        note = item["signature"] or ""
        if note or item["hint"]:
            tag = f"[{note}] " if note else ""
            lines.append(f"{'':>10} {'':>6}  {'':<12} {'':>6}  └ {tag}{item['hint']}")
    if report["omitted"]["count"]:
        lines.append(
            f"另有 {report['omitted']['count']} 项(合计 {report['omitted']['size_human']})"
            f"低于阈值或超出 top,未列出"
        )
    return "\n".join(lines)
