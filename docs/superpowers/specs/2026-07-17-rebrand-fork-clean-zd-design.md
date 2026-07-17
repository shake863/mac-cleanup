# 设计文档：将 fork 改造为独立工具 `clean-zd`

日期：2026-07-17
仓库：`shake863/mac-cleanup`（默认分支 `master`）
上游：`mac-cleanup/mac-cleanup-sh`（默认分支 `main`，已不活跃，不再同步）

## 目标

把这个 fork 彻底改造成独立工具：改品牌名、把所有引用指向自己的 fork、移除只对原作者有意义的流程。今后不再从上游同步，因此不需考虑 git 合并冲突。工具改名为 **`clean-zd`**，与原版 `mac-cleanup` 天然区分、可并存安装。

## 改动范围

### 1. 可执行脚本：`mac-cleanup` → 重命名为 `clean-zd`

用 `git mv mac-cleanup clean-zd` 重命名（命令名 = 文件名，避免割裂）。脚本内改动：

- **usage() 帮助文本**（约 17-18 行）：`A Mac Cleaning up Utility by fwartner` 与 `https://github.com/mac-cleanup/mac-cleanup-sh` → 改为你的署名和 `https://github.com/shake863/mac-cleanup`。
- 第 15 行 `$(basename "${BASH_SOURCE[0]}")` 动态取名，重命名后自动显示 `clean-zd`，无需改。
- **第 134 行注释** `until mac-cleanup.sh has finished` → `clean-zd`。
- **第 210 行 bug 修复**：上游遗留的硬编码 `/Users/wah/Library/Developer/CoreSimulator/...` 改为 `~/Library/Developer/CoreSimulator/...`。此行仅在 dry-run 的模拟器分支命中。
- 清理逻辑本身不动：conda / pnpm / 腾讯会议 / 额外 Xcode 与 Application Support 缓存等定制全部保留。

### 2. installer.sh：三种安装方式保留并改指向 fork

- curl/wget raw 地址：`mac-cleanup/mac-cleanup-sh/main/mac-cleanup` → `shake863/mac-cleanup/master/clean-zd`（注意分支 main → master）。
- 安装目标：`/usr/local/bin/mac-cleanup` → `/usr/local/bin/clean-zd`。
- 下载后的本地文件名 `mac-cleanup` → `clean-zd`。
- installer 顶部 usage 里的项目链接 → 指向 fork。

### 3. README.md

- 标题与描述改为 `clean-zd`。
- Homebrew 安装：`brew tap shake863/tap` + `brew install shake863/tap/clean-zd`；标注"需自建 `shake863/homebrew-tap` 仓库后生效"。
- curl / wget / 手动安装的所有 URL、文件名、`cleanup` 调用名 → `clean-zd` 与 fork 地址。
- 更新（update）、卸载章节同步。
- 功能列表（What does script do）保留，可补充定制项（conda / pnpm / 腾讯会议）。

### 4. release workflow（.github/workflows/release.yml）

- 删除 `tweet` job（原作者专属）。
- `homebrew` job：`formula-name: clean-zd`、`homebrew-tap: shake863/homebrew-tap`、`base-branch: master`、`formula-path: Formula/clean-zd.rb`。
- 保留 tag 触发机制。

### 5. LICENSE / CHANGELOG

- **LICENSE**：MIT，保留原作者版权行不动（法律要求）。
- **CHANGELOG.md**（当前为空）：加一条初始条目，说明这是基于 mac-cleanup 的定制 fork。

## 不做的事

- 不改清理业务逻辑。
- 不做无关重构（仅修第 210 行这个改造范围内碰到的 bug）。
- 不动 LICENSE 版权归属。

## 验证方式

1. `shellcheck clean-zd` 与 `shellcheck installer.sh` 无新增问题。
2. `./clean-zd -d`（dry-run，非破坏性）跑通，帮助文本与命令名正确。
3. `grep -rn 'fwartner\|mac-cleanup-sh\|/wah/' .`（排除 LICENSE、本 spec）确认无遗漏上游引用。
