# clean-zd AI 清理助手设计(v2)

日期:2026-07-18
状态:已确认
取代:[2026-07-18-scan-manifest-design.md](2026-07-18-scan-manifest-design.md)(v1,Bash 扫描-清单方案,未实施即被本设计取代)

## 背景与目标

v1 设计在 Bash 脚本上加「扫描 → 确认 → 记录 → 复用」机制。讨论后目标升级:在传统格式化清理的基础上,打造 **AI 驱动的 Mac 清理助手**,最终以 skill 形式交付给 AI(Claude Code)驱动;AI 能自主判断的项直接给结论,判断不清的项交互式与用户讨论。

角色分工:

- **AI(经 skill)是判断者**:多数候选项(已知 app 缓存、开发产物)AI 可直接判断并给出理由;
- **用户是最终仲裁者**:仅 AI 拿不准的项通过 AskUserQuestion 交互确认;
- **工具是确定性执行者**:扫描、记录、删除是结构化输入输出的程序,自身无 AI。

Bash 无法良好承载结构化 JSON 输出、清单状态管理与安全校验,故执行层改用 Python(stdlib-only,零第三方依赖,依赖系统 python3)。

## 总体架构(三层)

```
智能层  skill(market-zd 仓库,薄壳)
        工作流:扫描→AI逐项判断(给理由)→拿不准的问用户→写清单→dry-run→确认→清理→沉淀规则
                    │ 调用 CLI、读写 JSON
知识层  数据(~/.config/clean-zd/ 本机 + 仓库内规则库)
        rules.json(仓库,内置通用规则)   manifest.json / ignore.json(本机)
        safety 排除名单(内置于引擎,硬编码)
执行层  Python CLI(mac-cleanup 仓库,stdlib-only,自身无 AI)
        clean-zd scan / manifest / clean / status
```

**安全铁律:AI 永远不直接删文件。** AI 只能通过 `manifest add` 写清单条目,写入时引擎硬校验;删除只发生在 `clean-zd clean` 内部,受硬编码守卫约束。AI 判断可以错,爆炸半径被执行层封顶。

## 执行层:Python CLI

单入口 `clean-zd`(python3 脚本),子命令:

### `clean-zd scan [--category cache|dev|leftover|bigfile|system] [--json]`

只读扫描,永不删除。输出候选项列表(`--json` 供 AI,默认表格供人),每项含:路径、体积、类别、证据(如「对应 app 不存在」「90 天未访问」)、风险分级(`recommend` / `caution`)、建议策略。已在 manifest / ignore / safety 名单中的路径不出现——每次扫描只出现新面孔,形成迭代闭环。

五类候选来源:

1. **缓存/日志**:`~/Library/Caches/*`、`~/Library/Logs/*`、`~/Library/Application Support/*/Cache(s)`、沙盒应用容器内缓存 `~/Library/Containers/<bundleID>/Data/Library/Caches`(App Store / 沙盒应用如微信的缓存大头在此),以及 darwin per-app 临时缓存目录 `$(getconf DARWIN_USER_CACHE_DIR)/<bundleID>`(即 `/private/var/folders/.../C/`,lemon-cleaner 的 SystemTempDir),按体积排序;
2. **开发产物**:Xcode DerivedData/模拟器/Device Support、Docker、npm/pip/go/conda 等缓存中 rules.json 未覆盖的部分;
3. **卸载残留**:在 `/Library` 与 `~/Library` 两级的 Application Support、Caches、Preferences、Saved Application State、Logs、Containers、LaunchAgents、LaunchDaemons、StartupItems、CrashReporter、DiagnosticReports、WebKit 下寻找「孤儿」目录(目录集参考 lemon-cleaner LMSearchPath)。匹配算法(参考 lemon-cleaner Uninstaller):
   - **已装应用身份集**:遍历 `/Applications`(及 `~/Applications`),用 stdlib `plistlib` 读各 app `Info.plist`,取 bundleID、appName、executableName、显示名四元组构建存在集;
   - **孤儿判定**:候选目录名与存在集做 bundleID 精确/前缀匹配 + 名称小写前缀匹配,均不命中才判为孤儿候选;
   - **厂商前缀保护**(防误报关键):如 `com.tencent.xxx` 残留,若机器仍装有其他 `com.tencent.*` 应用,不判定为孤儿;
   - **别名映射**:App 名与数据目录名不一致的特例(如有道词典 ↔ `com.youdao.YoudaoDict`)维护在 rules.json 的 `aliases` 段;
   - **pkgutil 收据**:`pkgutil --pkgs` 识别 pkg 安装的软件,首版仅用于候选项的证据展示;
   - 判断保守,仅列候选,永不自动判定;
4. **大文件发现**:默认扫 `~/Downloads` 与 `~/Desktop`,阈值默认 500MB,目录与阈值可参数调整;
5. **系统项**:垃圾箱、Mail Downloads、旧 iOS 备份的体积报告(风险分级一律 `caution`)。

### `clean-zd manifest add/remove/list`

清单管理。`add` 时安全校验,不过即拒绝写入:

- 路径实际存在且位于 `$HOME` 内(垃圾箱等少数系统项走白名单例外);
- 不在 safety 排除名单;
- 拒绝空路径、根路径、`$HOME` 本身、裸 glob、经软链逃逸出 `$HOME` 的路径。

### `clean-zd clean [--dry-run] [--purge]`

统一执行 rules.json(通用规则)+ manifest.json(本机清单)。

- `--dry-run`:只统计各项体积与总计,非破坏;command 型规则只报告将执行的命令;
- 默认真删走废纸篓优先(移入 Trash),`--purge` 才直接 rm;
- `delete` 策略条目清理成功后自动从 manifest 移除;`empty-dir` 条目长期保留复用;
- 执行前对每条再次跑安全校验,校验不过跳过并警告,不中断整体。

### `clean-zd status`

清单概况、上次清理时间、累计释放空间。

## 知识层:数据

### `rules.json`(仓库内,随版本发布)

现 Bash 脚本所有硬编码清理块转译为规则条目,两种类型:

- **`path` 型**:字段 `id / title(人读名) / tips(为什么可清,同时喂给 AI 与用户展示) / risk(recommend|caution) / paths[] / match(文件名 glob 或正则,可选) / exclude[](条目级排除路径/模式,可选) / min_size(可选) / older_than_days(可选) / depth(扫描深度:0=路径本身,1=一层子项,-1=递归,默认 1) / strategy(empty-dir 清空目录保留目录 | delete 删除路径本身)`。schema 参考 lemon-cleaner 规则库的表达能力(大小/时间/名称条件、深度控制、条目级排除),但用扁平字段,不引入其 filter 编号引用与表达式代数;
- **`command` 型**:`id / title / tips / command(工具原生清理命令,如 brew cleanup、docker system prune、npm cache clean、conda clean)/ guard(type 检测)`。

另有 **`aliases` 段**:App 名与数据目录名不一致的映射特例,供 leftover 扫描使用。

转译时按 lemon-cleaner 的 Xcode 清理项(DerivedData、iOS/macOS Device Support、Archives、Device Logs、DocumentationCache、Simulator、Simulator Runtimes)核对补全现有覆盖。

明确不吸收 lemon-cleaner 的:filter 表达式引擎(编号引用 + 代数组合,可维护性差)、无用语言文件清理(风险高收益低)、微信媒体分类深度定制(待清单迭代机制成熟后自然演进)。

### safety 排除名单(引擎内硬编码,非用户可改文件)

lemon-cleaner 历史积累的规则知识已系统提炼为 [docs/reference/lemon-cleaner-knowledge.md](../../reference/lemon-cleaner-knowledge.md)(安全排除名单及原因、条件规则模式、清理项知识表、机制性知识,含落地对照表)。safety 名单以该文档 §1.1/§1.2 为种子手工编写(不搬运其 GPL XML):系统关键缓存(dock、FontRegistry、LaunchServices、IconServices、appstoreagent 等)与「应用数据混在缓存目录」类(Logic Pro、1Password、游戏存档等)。作用于两处:scan 永不出候选;manifest add 永拒写入。

**rules.json 初始内容的三个种子来源**:① 现 Bash 脚本清理块转译;② lemon-cleaner 知识提炼文档(§3 清理项知识表,含风险标记、浏览器「只清 Cache 子目录」等经验);③ 上线后 AI/用户迭代沉淀。

### `manifest.json` / `ignore.json`(`~/.config/clean-zd/`,本机专属,不进 git)

字段:`path`、`type`(候选类别)、`strategy`、`risk`、`reason`(AI 或用户的判断理由)、`decided_by`(`ai` / `user`)、`added`(日期)。`ignore.json` 记「确认不清」,供扫描过滤。

## 智能层:skill(market-zd 仓库,`plugins/<name>/` 结构,薄壳)

SKILL.md 只写工作流与判断准则,不含实现逻辑:

1. `clean-zd scan --json` 获取候选;
2. AI 逐项判断:认识的直接给结论 + 理由(如「微信缓存,可清,会重新生成」);
3. 拿不准的(未知目录、大文件、疑似残留)→ AskUserQuestion 问用户,附上下文(体积/最后修改时间/归属推测);
4. 结论写入 manifest / ignore(带 reason、decided_by);
5. `clean --dry-run` 向用户展示预计释放空间 → 用户确认 → `clean`;
6. **沉淀闭环**:发现有普适价值的规则,提示用户将其提交进 mac-cleanup 仓库 rules.json——个人清单是试验田,规则库是沉淀层。

判断准则(写入 skill):缓存/日志等可再生项 AI 可自主判断;删除类(不可再生文件)必须问用户;凡 `risk=caution` 一律问用户。

## 存量处置与交付

- Bash `clean-zd`、`installer.sh` 退役删除;README、安装方式、Homebrew tap / release workflow 改为 Python 版。退役动作在转译完成且 dry-run 对比验证通过后执行;
- 交付形态:装引擎(mac-cleanup)+ 在 Claude Code 装 skill(market-zd),即得完整 AI 清理助手;引擎单独可人工使用(scan 表格输出 + 手动 manifest add)。

## 后续迭代(首版不含)

- 项目目录(如 `~/github`)下陈旧 `node_modules` 扫描;
- **体积缓存**:`~/.config/clean-zd/sizecache.json` 缓存目录体积、按 mtime 失效,加速重复扫描(参考 lemon-cleaner QMScanFileSizeCacheManager);
- pkgutil 收据的完整残留清单(首版仅作证据展示)。

## 验证

- 引擎:stdlib `unittest` 覆盖安全校验、规则解析、dry-run 统计;`scan` 只读可直接真跑;`clean --dry-run` 输出与旧 Bash `clean-zd -d` 对比,校验规则转译完整性;
- 人工构造非法 manifest 条目(根路径、$HOME 外、safety 名单内)验证「拒写入 + 执行时跳过并警告」;
- skill:本机真实走一遍完整工作流(扫描→判断→问询→清单→dry-run→清理)。
