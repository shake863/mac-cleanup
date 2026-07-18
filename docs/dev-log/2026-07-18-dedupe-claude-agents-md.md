# 2026-07-18 消除 CLAUDE.md 与 AGENTS.md 的内容重复

## 背景 / 目标

仓库同时有 `CLAUDE.md`(供 Claude Code)和 `AGENTS.md`(供 Codex,适配其全局约定风格)。两者正文逐字重复,后续任一改动都要两处同步,迟早漂移。目标:单一真实来源,零重复。

## 方案依据

Claude Code 官方 memory 文档(https://code.claude.com/docs/en/memory.md)专门有 AGENTS.md 一节:

- Claude Code **只读 `CLAUDE.md`,不读 `AGENTS.md`**(无版本原生支持,无 settings 重定向)。
- 标准去重做法:让 `CLAUDE.md` 通过 `@path` import 或 symlink 指向 `AGENTS.md`。因 Codex 只读 `AGENTS.md`,**内容真身必须放 `AGENTS.md`,`CLAUDE.md` 当薄壳**。
- 方向固定为 `CLAUDE.md` → `AGENTS.md`,反之会让 Codex 把 `@` import 语法当字面文本看到。

采用 import 方案(比 symlink 更灵活,便于将来加 Claude 专属补充,且避免跨平台 symlink 麻烦)。

## 改动内容

- `CLAUDE.md`:整份内容替换为一行 `@AGENTS.md`(薄壳,导入内容真身)。
- `AGENTS.md`:保留全部正文;第 3 行由"guidance to Codex"中性化为"guidance to AI coding assistants (Claude Code, Codex, etc.)",避免 Claude 上下文里出现"guidance to Codex"。

## 验证

- `CLAUDE.md` 仅含 `@AGENTS.md`;`AGENTS.md` 正文完整、第 3 行已中性化。
- `AGENTS.md` 不含任何 `@` import,无循环导入风险(官方 import 上限 4 跳)。
- import 在启动时展开进上下文;后续可在真实会话用 `/context` 确认已加载。

## 后续

- 将来若需 Claude 专属说明,在 `CLAUDE.md` 的 `@AGENTS.md` 下方追加 `## Claude Code` 章节即可,不影响 Codex。
- 所有共享文档内容今后只改 `AGENTS.md` 一处。
