from __future__ import annotations

import fnmatch
import glob
import json
import time
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
    strategy: str = "empty-dir"
    depth: int | None = None
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


def load_rules(
    path: Path | None = None,
) -> tuple[list[PathRule], list[CommandRule], dict]:
    data = json.loads((path or rules_file()).read_text())
    path_rules = [PathRule(**item) for item in data.get("path_rules", [])]
    command_rules = [CommandRule(**item) for item in data.get("command_rules", [])]
    return path_rules, command_rules, data.get("aliases", {})


def _bases(rule: PathRule) -> list[Path]:
    output: list[Path] = []
    for raw in rule.paths:
        expanded = str(expand(raw))
        if any(character in expanded for character in "*?["):
            output += [Path(path) for path in sorted(glob.glob(expanded))]
        elif Path(expanded).exists():
            output.append(Path(expanded))
    return output


def _keep(rule: PathRule, path: Path) -> bool:
    if rule.match and not fnmatch.fnmatch(path.name, rule.match):
        return False
    for pattern in rule.exclude:
        expanded_pattern = str(expand(pattern))
        if fnmatch.fnmatch(str(path), expanded_pattern) or str(path).startswith(
            expanded_pattern
        ):
            return False
    try:
        stat = path.lstat()
    except OSError:
        return False
    if rule.min_size and not path.is_dir() and stat.st_size < rule.min_size:
        return False
    if (
        rule.older_than_days
        and time.time() - stat.st_mtime < rule.older_than_days * 86400
    ):
        return False
    return True


def rule_targets(rule: PathRule) -> list[Path]:
    depth = rule.effective_depth()
    targets: list[Path] = []
    for base in _bases(rule):
        if depth == 0 or not base.is_dir():
            candidates = [base]
        elif depth == 1:
            candidates = sorted(base.iterdir())
        else:
            candidates = sorted(path for path in base.rglob("*") if not path.is_dir())
        targets += [path for path in candidates if _keep(rule, path)]
    return targets
