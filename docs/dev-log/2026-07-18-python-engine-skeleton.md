# 2026-07-18 Python 引擎骨架

## 背景 / 目标

`clean-zd` v2 将从单文件 Bash 工具迁移为 Python 标准库实现的三层架构。本任务先建立可持续扩展的包结构、命令行分发和基础路径工具，同时保留旧 Bash 脚本供后续对比验证。

## 改动内容

- 将旧 `clean-zd` 移至 `legacy/clean-zd.bash`，保留可执行位和 Git 历史。
- 新增 Python 启动器 `clean-zd` 与 `cleanzd` 包，提供 `scan`、`manifest`、`clean`、`status` 四个子命令的参数骨架。
- 新增 `cleanzd.paths`，实现配置目录、环境变量与用户目录展开、容量格式化、容错递归计量。
- 新增 `tests/test_paths.py` 与 `tests/test_cli.py`，覆盖路径工具和 CLI 基础行为。

## 验证方式

- `python3 -m unittest discover -s tests -v`
- `./clean-zd status`

## 遗留 / 后续

- `scan`、`manifest`、`clean` 目前仅完成参数解析，具体分发由后续任务接入。
- `status` 当前输出骨架就绪提示，真实统计逻辑将在 T6 实现。
- 旧 Bash 脚本保留到 T10，待新旧 dry-run 对比完成后退役。

## 相关文档或提交

- 设计：`docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`
- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 1
- 提交：本任务提交
