# 2026-07-18 rules 规则引擎

## 背景 / 目标

`clean-zd` v2 需要把旧 Bash 中分散的清理逻辑承载到可读取的 JSON 规则库。本任务先实现与具体规则数据解耦的规则模型、加载器和目标路径求值，为后续规则库与清理执行器提供统一接口。

## 改动内容

- 新增 `PathRule` 和 `CommandRule` 数据类，覆盖风险、策略、深度、名称、排除、体积和时间条件。
- 新增 `rules_file` 与 `load_rules`，将 JSON 中的路径规则、命令规则和别名表解析为运行时对象。
- 新增路径 glob 展开和目标枚举，支持深度 0、1、-1，以及由策略推导默认深度。
- 新增 `match`、`exclude`、`min_size`、`older_than_days` 过滤求值。
- 新增 10 个单元测试，覆盖所有规定的枚举与过滤行为。

## 验证方式

- `python3 -m unittest tests.test_rules -v`
- `python3 -m unittest discover -s tests -v`

## 遗留 / 后续

- `cleanzd/rules.json` 将由 T5 提供，本任务不写入具体清理规则。
- T6 清理执行器将消费本模块的加载与求值结果，并在执行前叠加 safety 复检。

## 相关文档或提交

- 设计：`docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`
- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 4
- 提交：本任务提交
