from __future__ import annotations

import fnmatch
from pathlib import Path

from .paths import expand


class SafetyError(Exception):
    """路径未通过安全校验。"""


# 出处与原因见 docs/reference/lemon-cleaner-knowledge.md
# §1.1(系统关键缓存)/§1.2(应用数据混在缓存目录)
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
    "Logic Pro",
    "com.apple.logic",
    "com.apple.STMExtension",
    "1Password",
    "IINA",
    "Aerial",
    ".DocumentRevisions-V100",
    ".app/",
)


def safety_hit(path: Path) -> str | None:
    value = str(path)
    for pattern in SAFETY_GLOBS:
        if fnmatch.fnmatch(value, str(expand(pattern))):
            return pattern
    for substring in SAFETY_SUBSTRINGS:
        if substring in value:
            return substring
    return None


def validate_target(path: Path, home: Path | None = None) -> Path:
    home = (home or Path.home()).resolve()
    raw = Path(str(path))
    if any(character in str(raw) for character in "*?["):
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
