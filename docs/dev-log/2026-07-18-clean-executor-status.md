# 2026-07-18 clean 执行器与 status

## 背景 / 目标

在规则库、本机清单和 safety 守卫就绪后，本任务实现 `clean-zd` 的确定性清理执行层。执行器必须支持安全 dry-run、默认移入废纸篓、显式 purge、风险分级、命令规则、历史记录和清单生命周期管理。

## 改动内容

- 新增 `cleanzd/clean.py`，收集规则与 manifest 目标，计算体积并执行清理。
- `risk=caution` 默认跳过，只有 `--include-caution` 才纳入执行。
- 默认将目标移入 `~/.Trash`，重名时生成唯一后缀；`--purge` 才直接删除。
- 规则目标和 manifest 目标均在执行前调用 `validate_target` 复检，越界或命中安全名单时跳过并输出警告。
- `delete` manifest 条目清理成功后自动移除，`empty-dir` 条目保留并只清空子项。
- 执行命令规则并收集错误；真实清理结果追加到 `history.json`。
- 新增 `cleanzd/status.py`，展示清单、忽略名单、上次与累计清理概况。
- 将 `clean` 和 `status` 接入 CLI，支持中文文本与 JSON 报告。
- 新增 7 个执行器测试，覆盖 dry-run、purge、废纸篓、caution、清单生命周期、历史和规则越界拒绝。

## 验证方式

- `python3 -m unittest tests.test_clean tests.test_cli -v`
- `python3 -m unittest discover -s tests -v`
- `./clean-zd clean --dry-run`

真实 dry-run 只读统计 253 项、约 30.0GB，无 traceback；Spotlight 与 App Store 缓存命中 safety 后被正确跳过。

## 遗留 / 后续

- `scan` 与 `manifest` CLI 接线由 T7 完成。
- 真实非 dry-run 清理仍应由用户明确确认后触发；本任务验收未清理真实用户数据。

## 相关文档或提交

- 设计：`docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`
- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 6
- 提交：本任务提交
