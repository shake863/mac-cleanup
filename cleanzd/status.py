from __future__ import annotations

import json

from .config import load_ignore, load_manifest
from .paths import config_dir, human


def status_text() -> str:
    manifest = load_manifest()
    ignore = load_ignore()
    empty_dir_count = sum(1 for entry in manifest if entry.strategy == "empty-dir")
    lines = [
        f"清单条目: {len(manifest)}(empty-dir {empty_dir_count} / "
        f"delete {len(manifest) - empty_dir_count})",
        f"忽略名单: {len(ignore)}",
    ]
    history_file = config_dir() / "history.json"
    if history_file.exists():
        history = json.loads(history_file.read_text())
        if history:
            last = history[-1]
            lines.append(
                f"上次清理: {last['time']},释放 {human(last['freed_bytes'])}"
            )
            lines.append(
                f"累计清理 {len(history)} 次,共释放 "
                f"{human(sum(item['freed_bytes'] for item in history))}"
            )
    return "\n".join(lines)
