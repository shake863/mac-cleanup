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
        try:
            children = sorted(base.iterdir())
        except OSError:
            continue
        for child in children:
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
