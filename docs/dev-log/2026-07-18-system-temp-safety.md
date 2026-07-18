# 2026-07-18 SystemTempDir safety 盲区修复

## 背景 / 目标

T8 引入 darwin per-app SystemTempDir 扫描后，真实扫描发现 `com.apple.dock.extra`、`com.apple.FontRegistry`、`com.apple.Spotlight` 等系统关键缓存进入候选。它们与 safety 已保护的名称相同，但位置不在 `~/Library/Caches`，暴露了路径位置绑定造成的安全盲区。

## 改动内容

- 在 `cleanzd/safety.py` 增加系统关键缓存的路径组件 glob。
- 复用 §1.1 的 Dock、App Store、FontRegistry、LaunchServices、IconServices、Spotlight、Desktop Pictures、ColorSync 和屏保设置名称，不引入新的产品名单。
- `safety_hit` 在原有完整路径 glob 之外逐个检查路径组件，使同名关键缓存位于 SystemTempDir 时也能命中统一防线。
- 新增 SystemTempDir 三个真实名称的回归测试，以及普通缓存不误伤的对照测试。
- 同步更新 `docs/reference/lemon-cleaner-knowledge.md`，明确 §1.1 保护跨目录位置生效。

## 验证方式

- `python3 -m unittest tests.test_safety.SafetyHitTest -v`
- `python3 -m unittest tests.test_safety -v`
- `python3 -m unittest discover -s tests -v`
- `./clean-zd scan --category cache --json` 后检查关键名称候选

真实扫描得到 154 个缓存候选，Dock、FontRegistry、Spotlight 关键名称候选均为 0。

## 遗留 / 后续

- 后续新增缓存扫描来源时继续统一经过 `scan._admit` 与 `safety_hit`，不要在单一扫描器复制安全名单。
- T9/T10 可在本修复提交后继续。

## 相关文档或提交

- 知识来源：`docs/reference/lemon-cleaner-knowledge.md` §1.1、§4.1
- 触发提交：T8 `7ecf3d6`
- 提交：本任务提交
