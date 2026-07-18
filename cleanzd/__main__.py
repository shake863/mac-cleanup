from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clean-zd",
        description="AI 驱动的 Mac 清理助手(引擎)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_parser = sub.add_parser("scan", help="只读扫描,输出候选清理项")
    scan_parser.add_argument(
        "--category",
        action="append",
        choices=["cache", "dev", "leftover", "bigfile", "system"],
    )
    scan_parser.add_argument("--json", action="store_true")
    scan_parser.add_argument("--threshold-mb", type=int, default=500)
    scan_parser.add_argument("--dir", action="append")

    manifest_parser = sub.add_parser("manifest", help="本机清单管理")
    manifest_sub = manifest_parser.add_subparsers(dest="mcmd", required=True)
    manifest_add = manifest_sub.add_parser("add", help="登记可清条目(写入前安全校验)")
    manifest_add.add_argument("path")
    manifest_add.add_argument(
        "--strategy",
        required=True,
        choices=["empty-dir", "delete"],
    )
    manifest_add.add_argument(
        "--risk",
        default="recommend",
        choices=["recommend", "caution"],
    )
    manifest_add.add_argument(
        "--type",
        default="cache",
        choices=["cache", "dev", "leftover", "bigfile", "system"],
    )
    manifest_add.add_argument("--reason", default="")
    manifest_add.add_argument(
        "--decided-by",
        default="user",
        choices=["ai", "user"],
    )
    manifest_remove = manifest_sub.add_parser("remove", help="移除清单条目")
    manifest_remove.add_argument("path")
    manifest_list = manifest_sub.add_parser("list", help="列出清单与忽略名单")
    manifest_list.add_argument("--json", action="store_true")
    manifest_ignore = manifest_sub.add_parser("ignore", help="登记不清条目(扫描不再出现)")
    manifest_ignore.add_argument("path")
    manifest_ignore.add_argument("--reason", default="")
    manifest_ignore.add_argument(
        "--decided-by",
        default="user",
        choices=["ai", "user"],
    )

    clean_parser = sub.add_parser("clean", help="按规则库+清单执行清理")
    clean_parser.add_argument("--dry-run", action="store_true")
    clean_parser.add_argument("--purge", action="store_true", help="不进废纸篓,直接删除")
    clean_parser.add_argument("--include-caution", action="store_true")
    clean_parser.add_argument("--json", action="store_true")

    sub.add_parser("status", help="清单与清理历史概况")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        print("clean-zd v2 引擎骨架就绪(status 将在后续任务实现)")
        return 0
    print(f"子命令 {args.cmd} 尚未实现", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
