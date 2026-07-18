# 2026-07-18 规则目标枚举权限容错

## 背景 / 目标

T10 执行 `./clean-zd clean --dry-run --include-caution --json` 时，Trash 规则枚举 `~/.Trash` 触发 macOS TCC `PermissionError`，导致整个 dry-run traceback。路径计量和扫描器已经约定对不可读目录容错，规则目标枚举也必须保持同一行为。

## 改动内容

- 在 `rule_targets` 的 depth 0/1/-1 枚举边界统一捕获 `OSError`。
- 单个规则 base 不可读时跳过该 base，其余规则继续求值。
- 新增不可读 base 回归测试，使用最小 mock 稳定模拟系统权限异常，断言返回空目标而不是传播异常。

## 验证方式

- `python3 -m unittest tests.test_rules.RuleTargetsTest.test_unreadable_base_yields_nothing -v`
- `python3 -m unittest discover -s tests -v`
- `./clean-zd clean --dry-run --include-caution --json`

修复后全量 59 个测试通过；真实 dry-run 输出 479 项、42.0GB、0 errors，无 traceback。

## 遗留 / 后续

- T10 对照另发现 Minecraft 规则数据遗漏，已将 T5 退回 Trae；旧 Bash 退役需等待 T5 修复后继续。

## 相关文档或提交

- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 10
- 提交：本任务提交
