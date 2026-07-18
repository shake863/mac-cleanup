# 2026-07-18 clean-zd v2 Python 重写

## 背景 / 目标

旧版 `clean-zd` 是约 500 行的 Bash 单文件，只能按硬编码路径直接清理，难以承载结构化扫描、清单状态、安全校验和 AI 协作。v2 按 [AI 清理助手设计](../superpowers/specs/2026-07-18-ai-cleaner-design.md) 重写为 Python 3.9+ 标准库引擎，实现“扫描 → 判断 → 记录 → dry-run → 确认 → 清理 → 沉淀”的闭环，并把 AI 的删除权限封顶在确定性执行层内。

## 改动内容

### 三层架构

- **执行层**：`cleanzd/` 提供 `scan`、`manifest`、`clean`、`status` 四个子命令，无 AI、无第三方依赖。
- **知识层**：仓库 `cleanzd/rules.json` 保存通用规则；本机 `~/.config/clean-zd/` 保存 manifest、ignore 和 history。
- **智能层**：外部 skill 读取 JSON 候选、给出理由、向用户询问高风险项并写入清单；AI 永不直接删除。

### 模块清单

- `paths.py`：配置目录、路径展开、体积统计与格式化。
- `safety.py`：系统关键排除名单、家目录边界、通配符/软链逃逸硬校验。
- `config.py`：manifest 与 ignore 的读写和去重。
- `rules.py` / `rules.json`：路径/命令规则模型、depth/match/exclude/size/age 求值及规则数据。
- `clean.py` / `status.py`：dry-run、废纸篓优先、purge、命令规则、历史和概况。
- `scan/`：缓存、开发产物、卸载残留、大文件与系统项扫描；统一过滤已决策项、规则覆盖项和 safety 命中项。
- `tests/`：全套标准库 `unittest` 回归。

### Bash 转译对照

旧 Bash 用非特权 dry-run shim 运行到 Continue 提示后中止，估算 46.19GiB；shim 只允许 sudo 凭据检查、保活和降级到当前用户的 `/usr/bin/du`，未执行任何特权或删除命令。Python `clean --dry-run --include-caution --json` 复验为 479 项、41.9GB、0 errors。

两者数值不要求相等：旧 Bash 包含 root/SIP 路径且 `du` 对部分目录无权限，Python v2 刻意限定用户态路径，并额外按命令规则 dry_paths 估算。对照验收以“每个旧清理块均被规则覆盖或明确放弃”为准。

覆盖结论：

- 用户缓存、Mail/CoreSimulator/JetBrains 日志、Adobe、Chrome、iOS 包与备份均有路径规则。
- Xcode DerivedData、Archives、Device Logs、DocumentationCache、watchOS、IB Support、CoreSimulator 均有规则，并按可再生性分级。
- Dropbox、Google Drive、Steam、Minecraft、Lunar Client、wget、Cacher、Android、Gradle、Kite、腾讯会议、Teams、Poetry、Java heap dump、Application Support/Caches 均被规则覆盖。
- brew、gem、Docker、npm、yarn、pnpm、CocoaPods、Go、conda、composer、simctl 均由命令规则覆盖；Pyenv 缓存由环境变量路径规则覆盖。
- 首轮逐块核对发现 Minecraft `launcher_cef_log.txt` 遗漏，T5 退回 rework 后由提交 `88094ff` 补齐，并增加规则数据回归测试。
- `--include-caution` 首次真实 dry-run 暴露 `~/.Trash` 权限异常，提交 `61e7ada` 为规则目标枚举补 `OSError` 容错和回归测试。
- 退役后的全类别真实 scan 暴露 TCC 保护的 `~/Desktop` 无法列举；bigfile 扫描器已在根目录枚举边界补 `OSError` 容错和回归测试，单个不可读来源不再中断整体扫描。

### 有意放弃清单

以下旧行为不进入 v2；它们需要 root/sudo、超出 `$HOME` 安全边界，或属于升级/系统流程而非用户态清理：

- `/Volumes/*/.Trashes`
- `/Library/Caches`
- `/System/Library/Caches`
- `/private/var/folders/bh/*/*/*/*` 裸 glob
- `/private/var/log/asl`
- `/Library/Logs/*` 中的 DiagnosticReports、CreativeCloud、Adobe 和 adobegc 日志
- DNS flush
- `sudo purge` 非活跃内存
- `brew -u` 的 update/upgrade 流程与 `brew tap --repair`
- Docker 自动启动/关闭流程

Google Drive 的强制 `killall` 也不迁移：v2 只负责清理目标，不擅自终止用户应用。需要工具原生命令的清理统一由 command rule 执行，不再复制旧 Bash 的进程编排。

### 存量退役

- 删除 `legacy/clean-zd.bash`、`installer.sh` 和旧 Homebrew `.github/workflows/release.yml`。
- README 改为 Python v2 安装、四子命令、安全约定和 skill 协作说明。
- AGENTS.md 改为 Python 三层架构、测试方式、rules schema 和安全铁律。

## 验证方式

- `python3 -m unittest discover -s tests -v`
- `./clean-zd status`
- `./clean-zd scan`
- `./clean-zd clean --dry-run`
- `./clean-zd clean --dry-run --include-caution --json`
- 全仓库检查当前 README/AGENTS 不再引用 installer、旧参数或 Homebrew release 流程。

最终回归包含 61 个单元测试；`status`、全类别 `scan`、默认 dry-run 与 include-caution JSON dry-run 均在真实本机环境运行，无 traceback。全类别 scan 输出 317 行候选信息；include-caution dry-run 为 479 项、约 42.0GB、0 errors。

## 遗留 / 后续

- 外部 `zd-mac-clean` skill 由计划 Task 11 交付，负责 AI 判断、用户问询和规则沉淀工作流。
- 后续可增加项目目录陈旧 `node_modules` 扫描。
- 后续可增加按 mtime 失效的目录体积缓存，加速重复扫描。
- pkgutil 收据目前不参与完整残留判断，可在后续增强证据展示。
- Homebrew tap/release 自动化已经退役；若未来恢复，应基于 Python v2 重新设计安装包与发布流程。

## 相关文档或提交

- 设计：`docs/superpowers/specs/2026-07-18-ai-cleaner-design.md`
- 实施计划：`docs/superpowers/plans/2026-07-18-ai-cleaner.md`
- 规则知识：`docs/reference/lemon-cleaner-knowledge.md`
- 引擎骨架：`5f4dfb5`
- safety：`d8e4220`、`8f37091`
- rules 引擎与权限容错：`e7017b7`、`61e7ada`
- clean/status：`6ac44bc`
- scan 与来源扫描器：`7ecf3d6`、`04710c1`
- rules 数据返工：`88094ff`
- v2 退役提交：本任务提交
