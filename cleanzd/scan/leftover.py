from __future__ import annotations

import plistlib
from pathlib import Path

from ..paths import expand, path_size
from ..rules import load_rules
from . import Candidate


SEARCH_DIRS = (
    "~/Library/Application Support",
    "~/Library/Caches",
    "~/Library/Preferences",
    "~/Library/Saved Application State",
    "~/Library/Logs",
    "~/Library/Containers",
    "~/Library/LaunchAgents",
    "~/Library/WebKit",
    "~/Library/HTTPStorages",
)

# 出处: docs/reference/lemon-cleaner-knowledge.md §1.4
EXCLUDE_PREFIXES = (
    "com.apple",
    "com.microsoft",
    "loginwindow",
    "usereventagent",
    "com.hex-rays.ida",
)
MIN_SIZE = 10 * 1024 * 1024


def installed_identities() -> tuple[set[str], set[str]]:
    bundles: set[str] = set()
    names: set[str] = set()
    for app_dir in ("/Applications", str(Path.home() / "Applications")):
        base = Path(app_dir)
        if not base.is_dir():
            continue
        for app in sorted(base.glob("*.app")):
            names.add(app.stem.lower())
            try:
                with open(app / "Contents" / "Info.plist", "rb") as file_handle:
                    info = plistlib.load(file_handle)
            except (OSError, plistlib.InvalidFileException):
                continue
            if info.get("CFBundleIdentifier"):
                bundles.add(str(info["CFBundleIdentifier"]))
            for key in ("CFBundleName", "CFBundleExecutable"):
                if info.get(key):
                    names.add(str(info[key]).lower())
    return bundles, names


def vendor_prefixes(bundles: set[str]) -> set[str]:
    return {
        ".".join(bundle.split(".")[:2]).lower()
        for bundle in bundles
        if "." in bundle
    }


def is_orphan(
    dirname: str,
    bundles: set[str],
    names: set[str],
    vendors: set[str],
    owned: set[str],
) -> str | None:
    lowered = dirname.lower()
    if dirname in owned:
        return None
    for prefix in EXCLUDE_PREFIXES:
        if lowered.startswith(prefix):
            return None
    if "steam" in lowered:
        return None
    if lowered.count(".") < 2:
        return None
    for bundle in bundles:
        bundle_lowered = bundle.lower()
        if (
            lowered == bundle_lowered
            or lowered.startswith(bundle_lowered + ".")
            or bundle_lowered.startswith(lowered + ".")
        ):
            return None
    for vendor in vendors:
        if lowered.startswith(vendor + "."):
            return None
    for name in names:
        if name and (lowered.startswith(name) or name.startswith(lowered)):
            return None
    return "形似 bundle id 且在已装应用中找不到对应(卸载残留候选)"


def scan() -> list[Candidate]:
    bundles, names = installed_identities()
    vendors = vendor_prefixes(bundles)
    _path_rules, _command_rules, aliases = load_rules()
    owned: set[str] = set()
    for bundle_id, dirnames in aliases.items():
        if bundle_id in bundles:
            owned.update(dirnames)
    output: list[Candidate] = []
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
                output.append(
                    Candidate(
                        str(child),
                        "leftover",
                        size,
                        f"{evidence};位于 {raw}",
                        "caution",
                        "delete",
                    )
                )
    return output
