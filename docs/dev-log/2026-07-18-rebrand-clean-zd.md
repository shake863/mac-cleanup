# 2026-07-18 改造为独立工具 clean-zd

## 背景 / 目标

本仓库是 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh) 的 fork。上游已不活跃,决定彻底改造成独立工具 `clean-zd`:改品牌名、所有引用指向本 fork(`shake863/mac-cleanup`)、移除原作者专属流程。今后不再从上游同步。

## 改动内容

- **重命名**:`mac-cleanup` → `clean-zd`(`git mv` 保留历史)。
- **引用全指向 fork**:脚本 usage、`installer.sh`、`README.md`(含 Homebrew tap 自建说明)、`.github/` 社区配置、`.github/workflows/release.yml`,全部指向 `shake863/mac-cleanup` 的 `master` 分支。
- **移除上游专属**:release workflow 的发推 job、README 的 opencollective 贡献者图、first-timers 模板里的原作者 Twitter 链接。
- **保留致谢**:LICENSE 版权行、README Credits、CHANGELOG 里指向上游的致谢链接。
- **bug 修复**:
  1. `clean-zd` 第 210 行硬编码 `/Users/wah/...` → `~/`(上游遗留)。
  2. conda/pnpm/腾讯会议/Xcode/Application Support 等定制清理块原本无 dry-run 守卫,`-d` 下会真删文件、conda 还会交互挂起。改用标准 `collect_paths`/`remove_paths` 模式 + conda 加 `type` 守卫和 `--yes`;删除与下方重复的裸 `pnpm store prune`。

## 验证

- `shellcheck clean-zd` 退出码 0 无告警;`bash -O extglob -n clean-zd` 语法通过。
- `installer.sh` 仅剩改造前既有的 SC2034 未使用变量告警(非回归)。
- 全仓库残留扫描:除有意保留的上游致谢链接外,无 `fwartner`/命令名/安装 URL/Twitter/opencollective 残留。
- `./clean-zd -h` 品牌显示正确。

## 遗留 / 后续

- Homebrew 发布需另建 `shake863/homebrew-tap` 仓库 + `HOMEBREW_TAP_GITHUB_TOKEN` 仓库 secret。
- `master` 领先 `origin/master`,尚未 push。

## 相关文档

- 设计:`docs/superpowers/specs/2026-07-17-rebrand-fork-clean-zd-design.md`
- 计划:`docs/superpowers/plans/2026-07-17-rebrand-fork-clean-zd.md`
- 合并提交:`5257101`(feature/rebrand-clean-zd → master,--no-ff)
