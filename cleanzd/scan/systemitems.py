from __future__ import annotations
from ..paths import expand, path_size
from . import Candidate

ITEMS = (
    ("~/.Trash", "废纸篓(清空前确认)"),
    ("~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads", "Mail 附件缓存"),
    ("~/Library/Application Support/MobileSync/Backup", "iOS 设备备份(确认已另有备份)"),
)

def scan() -> list[Candidate]:
    out = []
    for raw, title in ITEMS:
        p = expand(raw)
        if p.is_dir():
            size = path_size(p)
            if size >= 1024 * 1024:
                out.append(Candidate(str(p), "system", size, title, "caution", "empty-dir"))
    return out
