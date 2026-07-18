from __future__ import annotations

from ..paths import expand, path_size
from . import Candidate


MIN_SIZE = 50 * 1024 * 1024
KNOWN = (
    (
        "~/Library/Developer/Xcode/iOS DeviceSupport",
        "caution",
        "旧设备调试符号,连新设备会重建",
    ),
    (
        "~/Library/Developer/Xcode/macOS DeviceSupport",
        "caution",
        "旧设备调试符号",
    ),
    (
        "~/Library/Developer/CoreSimulator/Caches",
        "recommend",
        "模拟器缓存",
    ),
    ("~/Library/Caches/pip", "recommend", "pip 下载缓存"),
    ("~/.cargo/registry/cache", "recommend", "Rust registry 下载缓存"),
    ("~/.m2/repository", "caution", "Maven 本地仓库,重下耗时"),
    ("~/.docker", "caution", "Docker 数据根,建议用 docker system prune 处理"),
)


def scan() -> list[Candidate]:
    output = []
    for raw, risk, reason in KNOWN:
        path = expand(raw)
        if path.exists():
            size = path_size(path)
            if size >= MIN_SIZE:
                output.append(
                    Candidate(
                        str(path),
                        "dev",
                        size,
                        reason,
                        risk,
                        "empty-dir",
                    )
                )
    return output
