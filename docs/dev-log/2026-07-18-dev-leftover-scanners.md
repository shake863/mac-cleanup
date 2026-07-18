# 2026-07-18 dev 与 leftover 扫描器

## 背景 / 目标

`clean-zd scan` 已具备缓存、系统项和大文件来源，本任务补齐开发产物与卸载残留扫描。残留判定风险最高，因此只对形似 bundle id 的目录给出 caution 候选，并优先保护已装应用、同厂商应用、别名和排除名单。

## 改动内容

- `cleanzd/scan/dev.py` 扫描 Xcode Device Support、CoreSimulator、pip、Cargo、Maven 和 Docker 等固定开发目录，仅报告 50MB 以上项目。
- `cleanzd/scan/leftover.py` 从 `/Applications` 与 `~/Applications` 的 Info.plist 构建 bundle ID、应用名和可执行名身份集。
- 由 bundle ID 前两段构建厂商前缀；仍安装同厂商应用时保守放行相关数据目录。
- 对 Apple、Microsoft、IDA、Steam 等知识文档排除项直接放行。
- 读取 `rules.json` aliases，已装应用声明的别名目录不判残留。
- 仅对至少包含两个点、超过 10MB 且所有保护规则均未命中的目录生成 leftover caution 候选。
- 新增 8 个单元测试，覆盖 bundle、厂商、排除、别名、名称和保守格式门槛。

## 验证方式

- `python3 -m unittest tests.test_leftover -v`
- `python3 -m unittest discover -s tests -v`
- `./clean-zd scan --category leftover --category dev`
- 交叉检查真实候选与当前已装应用身份集和 Applications 目录。

真实扫描得到 3 个开发候选和 2 个 leftover 候选；两个残留候选分别属于迅雷 WebKit 数据与 TigerTrade 容器，当前身份集和 Applications 目录中均不存在对应应用。

## 遗留 / 后续

- leftover 永远只输出候选，不自动加入清单；删除前必须由 AI/用户复核。
- pkgutil 收据首版仍只作为后续证据增强方向，不参与当前孤儿判定。

## 相关文档或提交

- 设计：`docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`
- 知识来源：`docs/reference/lemon-cleaner-knowledge.md` §1.4、§4.2
- 计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md` Task 9
- 提交：本任务提交
