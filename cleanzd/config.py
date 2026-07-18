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
