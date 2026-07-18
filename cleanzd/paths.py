from __future__ import annotations

import os
from pathlib import Path


def config_dir() -> Path:
    env = os.environ.get("CLEAN_ZD_CONFIG_DIR")
    directory = Path(env) if env else Path.home() / ".config" / "clean-zd"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def expand(raw: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(raw)))


def human(nbytes: int) -> str:
    size = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)}B" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _physical_size(stat: os.stat_result) -> int:
    # 稀疏文件(如 Docker.raw)的 st_size 是逻辑大小,按 st_blocks 计物理占用,与 du 一致
    blocks = getattr(stat, "st_blocks", None)
    if blocks is None:
        return stat.st_size
    return blocks * 512


def path_size(path: Path) -> int:
    try:
        if path.is_symlink() or path.is_file():
            return _physical_size(path.lstat())
        if not path.is_dir():
            return 0
        total = 0
        # 硬链接共享同一 inode(如 conda 包文件),按 (st_dev, st_ino) 去重只计一次,与 du 一致
        seen_inodes = set()
        for root, _dirs, files in os.walk(path, onerror=lambda _error: None):
            for name in files:
                try:
                    stat = os.lstat(os.path.join(root, name))
                except OSError:
                    continue
                if stat.st_nlink > 1:
                    key = (stat.st_dev, stat.st_ino)
                    if key in seen_inodes:
                        continue
                    seen_inodes.add(key)
                total += _physical_size(stat)
        return total
    except OSError:
        return 0
