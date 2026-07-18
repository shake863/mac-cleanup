from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import load_manifest, save_manifest
from .paths import config_dir, expand, human, path_size
from .rules import CommandRule, load_rules, rule_targets
from .safety import SafetyError, validate_target


@dataclass
class CleanItem:
    source: str
    path: Path
    size: int
    strategy: str
    risk: str


def collect_items(
    include_caution: bool = False,
    rules_path: Path | None = None,
) -> tuple[list[CleanItem], list[CommandRule], list[str]]:
    items: list[CleanItem] = []
    warnings: list[str] = []
    path_rules, command_rules, _aliases = load_rules(rules_path)
    for rule in path_rules:
        if rule.risk == "caution" and not include_caution:
            continue
        for target in rule_targets(rule):
            try:
                validate_target(target)
            except SafetyError as error:
                warnings.append(
                    f"[safety] 跳过 {target}(规则 {rule.id}): {error}"
                )
                continue
            items.append(
                CleanItem(
                    f"rule:{rule.id}",
                    target,
                    path_size(target),
                    "delete",
                    rule.risk,
                )
            )
    for entry in load_manifest():
        if entry.risk == "caution" and not include_caution:
            continue
        path = expand(entry.path)
        try:
            validate_target(path)
        except SafetyError as error:
            if path.exists() or path.is_symlink():
                warnings.append(f"[safety] 跳过清单条目 {entry.path}: {error}")
            continue
        if entry.strategy == "empty-dir" and path.is_dir():
            for child in sorted(path.iterdir()):
                items.append(
                    CleanItem(
                        "manifest",
                        child,
                        path_size(child),
                        "delete",
                        entry.risk,
                    )
                )
        else:
            items.append(
                CleanItem(
                    "manifest",
                    path,
                    path_size(path),
                    "delete",
                    entry.risk,
                )
            )
    usable_commands = [
        command
        for command in command_rules
        if shutil.which(command.guard)
        and (include_caution or command.risk != "caution")
    ]
    return items, usable_commands, warnings


def dispose(path: Path, purge: bool) -> None:
    if purge:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        return
    trash = Path.home() / ".Trash"
    destination = trash / path.name
    suffix = 1
    while destination.exists() or destination.is_symlink():
        destination = trash / f"{path.name}.cleanzd-{int(time.time())}-{suffix}"
        suffix += 1
    shutil.move(str(path), str(destination))


def run_clean(
    dry_run: bool,
    purge: bool = False,
    include_caution: bool = False,
    rules_path: Path | None = None,
) -> dict:
    items, commands, warnings = collect_items(include_caution, rules_path)
    total = sum(item.size for item in items)
    report = {
        "dry_run": dry_run,
        "total_bytes": total,
        "items": len(items),
        "commands": [command.id for command in commands],
        "warnings": warnings,
        "freed_bytes": 0,
        "errors": [],
    }
    if dry_run:
        for command in commands:
            report["total_bytes"] += sum(
                path_size(expand(path)) for path in command.dry_paths
            )
        report["total_human"] = human(report["total_bytes"])
        return report
    freed = 0
    for item in items:
        try:
            dispose(item.path, purge)
            freed += item.size
        except OSError as error:
            report["errors"].append(f"{item.path}: {error}")
    for command in commands:
        try:
            subprocess.run(
                command.command,
                check=False,
                capture_output=True,
                timeout=1800,
            )
        except (subprocess.SubprocessError, OSError) as error:
            report["errors"].append(f"{command.id}: {error}")
    entries = load_manifest()
    kept = [
        entry
        for entry in entries
        if not (entry.strategy == "delete" and not expand(entry.path).exists())
    ]
    if len(kept) != len(entries):
        save_manifest(kept)
    report["freed_bytes"] = freed
    report["freed_human"] = human(freed)
    report["total_human"] = human(total)
    _append_history(report)
    return report


def _append_history(report: dict) -> None:
    history_file = config_dir() / "history.json"
    history = json.loads(history_file.read_text()) if history_file.exists() else []
    history.append(
        {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "freed_bytes": report["freed_bytes"],
            "items": report["items"],
            "errors": len(report["errors"]),
        }
    )
    history_file.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n"
    )
