# Changelog

## clean-zd

本项目 fork 自 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh)。

### 定制改动
- 重命名工具为 `clean-zd`，所有安装/引用指向 `shake863/mac-cleanup` fork。
- 新增 conda、pnpm、腾讯会议、额外 Xcode 与 Application Support 缓存清理。
- 修复上游遗留的硬编码模拟器路径（`/Users/wah/...` → `~/`）。
- 修复体积统计：改按物理占用（`st_blocks * 512`，与 `du` 同口径），稀疏文件（如 Docker.raw 虚拟磁盘）不再按逻辑大小虚高。
- 修复体积统计：目录遍历对硬链接按 `(st_dev, st_ino)` 去重只计一次（与 `du` 同口径），conda 等硬链接共享包文件的目录不再虚高（`~/anaconda3` 由 16GB 修正为 11GB）。
- 移除原作者专属的发推与 opencollective 内容。
