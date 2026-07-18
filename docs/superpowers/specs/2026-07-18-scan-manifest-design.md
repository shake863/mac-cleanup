# clean-zd 扫描-清单机制设计

日期:2026-07-18
状态:已被取代 — 见 [2026-07-18-ai-cleaner-design.md](2026-07-18-ai-cleaner-design.md)(目标升级为 AI 驱动清理助手,执行层改 Python,本文未实施)

## 背景与目标

clean-zd 目前是一份硬编码的已知缓存路径清单,只能清理脚本作者预先写死的位置。本设计为其加入「扫描 → 确认 → 记录 → 复用」机制:

1. 扫描本机,发现现有清单之外的可清理项(候选);
2. 交互式逐项人工确认,决定永久记录在本机清单中;
3. 下次清理时直接按清单执行,不再重复确认;
4. 每次扫描只出现「新面孔」,清单随使用不断迭代完善。

## 总体架构

```
clean-zd-scan (新脚本)          ~/.config/clean-zd/           clean-zd (现有脚本)
┌─────────────────┐            ┌──────────────┐             ┌─────────────────┐
│ 只读扫描 5 类来源  │──候选项──▶│ manifest.tsv  │──读取清单──▶│ 现有内置清理块     │
│ 交互逐项 y/n/s   │           │ ignore.tsv    │            │ + 新增:按清单清理  │
└─────────────────┘            └──────────────┘             └─────────────────┘
```

三个组成部分:

- **`clean-zd-scan`**(新增,Bash,零依赖):负责扫描、交互确认、维护清单。**只读,永不删除任何文件**。
- **`clean-zd`**(现有脚本):在内置清理块之后新增一个「自定义清单」清理块,读取 manifest 执行清理,完整遵循现有 `dry_run` 双路径模式(dry-run 时只 `collect_paths` 统计,真实运行才删除)。
- **`~/.config/clean-zd/`**(本机数据目录,不进 git):
  - `manifest.tsv` — 已确认「可清」的条目;
  - `ignore.tsv` — 已确认「不清」的条目,下次扫描不再询问。

清单是本机专属的(每台机器装的软件不同),不随仓库同步。

## 清单格式

Tab 分隔纯文本(Bash 易解析,人也可直接编辑):

```
# type	path	strategy	added	note
cache	~/Library/Caches/com.tencent.xinWeChat	empty-dir	2026-07-18	微信缓存
file	~/Downloads/Xcode_15.dmg	delete	2026-07-18	旧安装包
```

字段说明:

| 字段 | 含义 |
|---|---|
| type | 候选来源类别(cache / dev / leftover / bigfile / system) |
| path | 目标路径,`~` 开头,运行时展开 |
| strategy | 清理策略,见下 |
| added | 记入日期(YYYY-MM-DD) |
| note | 人读备注 |

两种清理策略:

- **`empty-dir`**:清空目录内容、保留目录本身。适合缓存/日志类;条目长期保留,每次清理复用——这是「记录后下次直接清」的主体。
- **`delete`**:删除该路径本身。适合一次性大文件、卸载残留;清理成功后条目自动从 manifest 移除。

`ignore.tsv` 只需 `path` 与 `added`(可带 note),用于扫描时过滤。

## 扫描器:5 类候选来源

1. **缓存/日志**:遍历 `~/Library/Caches/*`、`~/Library/Logs/*`、`~/Library/Application Support/*/Cache(s)`,按体积排序列出。
2. **开发产物**:Xcode DerivedData/旧模拟器、Docker、npm/pip/go 等缓存中 clean-zd 内置块**未覆盖**的部分。(扫描 `~/github` 等项目目录下陈旧 `node_modules` 首版不含,列为后续迭代。)
3. **卸载残留**:对比 `/Applications` 已装应用与 `~/Library/{Application Support,Caches,Preferences,Containers}` 下目录,找出对应应用已不存在的「孤儿」目录。判断保守,仅列候选,交人工确认。
4. **大文件发现**:默认扫描 `~/Downloads` 与 `~/Desktop`,列出超过阈值(默认 500MB,可通过参数调整)的文件/目录;扫描目录可通过参数追加。
5. **系统项**:垃圾箱、Mail Downloads、旧 iOS 备份的体积报告。

候选展示:路径、体积、类别、建议策略。交互选项:

- `y` — 记入 `manifest.tsv`(可清);
- `n` — 记入 `ignore.tsv`(不清,永不再问);
- `s` — 本次跳过,不记录,下次扫描仍会出现。

已存在于 manifest 或 ignore 中的路径不再作为候选出现——每次扫描只出现新面孔,形成迭代闭环。

## 安全设计

- 扫描全程只读;删除只发生在 `clean-zd` 执行清单块时,且受 dry-run 保护(`-d` 必须保持非破坏性,与仓库现有约定一致)。
- `clean-zd` 读取 manifest 时逐条校验:路径必须位于 `$HOME` 之下(垃圾箱等少数系统项走白名单例外);拒绝空路径、根路径、`$HOME` 本身、含裸 `*` 顶层 glob 等危险条目;校验不过的条目跳过并输出警告,不中断整体清理。
- 卸载残留只做候选建议,永不自动判定。

## 迭代沉淀

本机清单跑稳后,如某条规则有普适性(如某常用 app 的缓存路径),手动将其升级为 `clean-zd` 的内置清理块沉淀进仓库。本机清单是试验田,仓库脚本是沉淀层。

## 验证方式

- `shellcheck` 两个脚本;
- `clean-zd-scan` 只读,可直接真跑验证;
- `clean-zd -d` dry-run 验证清单块的体积统计与守卫逻辑;
- 人工构造假 manifest(含非法路径条目)验证校验逻辑:非法条目被跳过并警告,合法条目正常统计/清理。
