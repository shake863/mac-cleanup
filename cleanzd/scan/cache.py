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
            try:
                if not child.is_dir():
                    continue
            except OSError:
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
