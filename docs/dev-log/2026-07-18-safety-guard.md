# 2026-07-18 safety 路径安全守卫

## 背景 / 目标

`clean-zd` v2 允许规则库和本机清单向执行器提供清理路径，因此必须在扫描与删除逻辑之外建立不可绕过的硬安全边界。本任务依据 lemon-cleaner 知识提炼文档的 §1.1 和 §1.2，实现安全排除名单与目标路径校验。

## 改动内容

- 新增 `cleanzd/safety.py`，提供 `SafetyError`、`safety_hit` 和 `validate_target`。
- 将系统关键缓存、应用数据混存路径编码为不可由用户修改的 glob 与子串排除名单。
- 目标校验拒绝通配符、不存在路径、根目录、家目录本身、家目录外路径和软链逃逸。
- 校验时同时检查原始路径与 `resolve` 后路径，避免通过软链或路径表现形式绕过安全名单。
- 新增 9 个单元测试，覆盖安全命中、正常缓存放行和各类非法目标拒绝。

## 验证方式

- `python3 -m unittest tests.test_safety -v`
- `python3 -m unittest discover -s tests -v`

## 遗留 / 后续

- 本任务只落地 §1.1/§1.2；专项扫描排除与残留扫描排除分别由后续扫描器任务处理。
- 清理执行器仍需在执行每条规则和清单项之前调用 `validate_target` 复检。

## 相关文档或提交

- 知识来源：`docs/reference/lemon-cleaner-knowledge.md` §1.1、§1.2
- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 2
- 提交：本任务提交
