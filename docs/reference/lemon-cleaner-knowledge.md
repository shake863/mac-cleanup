# lemon-cleaner 规则知识提炼

来源:[Tencent/lemon-cleaner](https://github.com/Tencent/lemon-cleaner)(本地克隆 `~/github/lemon-cleaner`)的规则库与代码,主要文件:

- `LemonClener/LemonClener/libcleaner/garbage1_zh.xml`(主规则库,version 2024.03.21.1)
- `LemonClener/LemonClener/libcleaner/garbage_appstore_zh.xml`(App Store 沙盒版规则)
- `localPod/LemonUninstaller/`(卸载残留搜索与匹配)

**许可说明**:lemon-cleaner 为 GPL v3,本文档是对其规则中**事实性知识**(路径、条件、风险结论)的人工提炼与重述,附出处备查;不逐字搬运其 XML/代码。据此手工编写我们自己的 `rules.json` 与 safety 名单。

**用途**:clean-zd v2(AI 清理助手)实施时,本文档是 ① 引擎硬编码 safety 排除名单、② `rules.json` 初始规则、③ 扫描器行为设计的三个种子来源之一(另两个:原 Bash 脚本转译、后续 AI/用户迭代沉淀)。

---

## 1. 安全排除名单(永不清理/永不出候选)

这是 lemon 多年用户反馈换来的「碰了会出事」名单。分组如下,注明原因的是 XML 注释里明说的。

### 1.1 系统关键缓存(清了系统功能异常)

| 路径/模式 | 原因 |
|---|---|
| `~/Library/Caches/com.apple.dock`、`com.apple.dock.iconcache` | Dock 图标缓存,清后 Dock 异常 |
| `~/Library/Caches/com.apple.appstore`、`com.apple.appstoreagent` | 清后 App Store 待更新列表无法显示(macOS 15 实测) |
| `com.apple.FontRegistry` | 字体注册缓存 |
| `com.apple.LaunchServices-*` | 应用关联数据库 |
| `com.apple.IconServices` | 图标服务缓存 |
| `com.apple.Spotlight` | Spotlight 索引 |
| `~/Library/Caches/Desktop Pictures/` | 桌面壁纸缓存 |
| `~/Library/Caches/ColorSync/` | 色彩配置 |
| `~/Library/Caches/com.apple.preference.desktopscreeneffect.desktop/` | 屏保设置 |
| `/.DocumentRevisions-V100/` | 系统文件版本库(lemon 标 recommend=NO 的 soft 类型,实质极危险) |

> `com.apple.dock*`、`com.apple.appstore*`、`com.apple.FontRegistry*`、`com.apple.LaunchServices-*`、`com.apple.IconServices*`、`com.apple.Spotlight*` 等系统关键名称也可能出现在 darwin per-app SystemTempDir(`/private/var/folders/.../C/`)。clean-zd 的 safety 防线按路径组件名称统一保护,不只匹配 `~/Library/Caches` 下的位置。

### 1.2 应用数据混在缓存目录(清了丢用户数据)

| 路径/模式 | 原因 |
|---|---|
| `Logic Pro`、`com.apple.logic*`、`com.apple.STMExtension`、路径含 `Logic` | Logic Pro 音频素材库,误删损失大 |
| `1Password`(路径含) | 清语言包/缓存会误删其浏览器插件 |
| `IINA` | 是 Safari 插件,清语言包受影响 |
| `Aerial`(路径含) | 屏保视频素材,重新下载代价大 |
| `codes.rambo.AirCore` | AirBuddy 数据 |
| 游戏类:`com.rovio.mac.badpiggies`、`com.naturalmotion.csrracingmac`、`com.glu.macos.{ewarriors2,ckzombies2,deerhunt2}` | 游戏存档存在缓存目录里 |
| `Axure-*` | Axure 数据 |
| 路径含 `.app` | 避免删到应用本体内部 |

### 1.3 专项规则接管、通用扫描不碰(避免重复/误伤)

浏览器与大厂 IM 的缓存由专门规则精确处理(见 §3.3/§3.4),通用缓存扫描一律排除:

- 浏览器:`~/Library/Caches/{Google,QQBrowser2,Firefox,Opera,com.google.Chrome,com.apple.Safari,com.apple.Safari.SafeBrowsing,com.apple.safaridavclient,Microsoft*}`、`~/Library/Containers/com.apple.Safari.CacheDeleteExtension/`
- IM/办公:`~/Library/Containers/com.tencent.qq*`、`~/Library/Containers/com.tencent.xinWeChat*`、`~/Library/Caches/com.tencent.xinWeChat/`、`~/Library/Caches/com.alibaba.DingTalkMac*`、`~/Library/Containers/5ZSL2CJU2T.com.dingtalk.mac*`
- IDE:`~/Library/Caches/IntelliJIdea*`(JetBrains 缓存重建代价大,lemon 选择不碰)
- 微软全家:`~/Library/Containers/com.microsoft.*`、`/private/var/folders/*/*/com.microsoft.*`
- `~/Library/Caches/Metadata/`、`DiagnosticReports`(由日志专项处理)

> 对我们的含义:这组「专项接管」名单在 clean-zd v2 中的角色 = scan 的排除名单;其中微信/QQ/钉钉等的精确清理路径可作为后续 rules.json 专项规则的候补。

### 1.4 卸载残留判定的排除(不当作孤儿残留)

来自残留扫描 filters:文件名匹配 `com.microsoft.office*`、`*com.apple*`、`loginwindow*`、`UserEventAgent*`、`com.hex-rays.IDA*`、`*.[sS]team*`(Steam 游戏库!);bundleid 前缀 `com.apple`、`com.microsoft`、`com.ittybittyapps`;以及**已签名(signed)应用**整体排除。

---

## 2. 条件规则模式(带条件才清)

| 目标 | 条件 | 出处 |
|---|---|---|
| `/private/var/log/`、`~/Library/Logs/` 下日志 | 体积 > 10KB **且** 名称匹配 `access.log*` / `page.log*` / `error.log*` / `*.out` / `*.log.*` / `*log` 结尾 | filter 8~14 |
| QQ 消息缓存 | 按时间分档:>180 天 / <180 天(风险不同) | filter 61/62 |
| 微信 | `avatar` 目录排除(头像缓存清了全员头像重新拉取) | filter 63 |
| iOS 照片缓存 `~/Pictures/iPod Photo Cache/` | 子文件数 > 1 且存在 `Photo DataBase` 子路径(确认真是照片缓存库才清) | filter 40/41 |
| Opera 缓存 | 按 app 版本号选不同缓存路径(appversion 正则条件) | item 309 |

> 对我们的含义:验证了 rules.json 需要 `min_size` / `older_than_days` / `match` / `exclude` 字段;「按版本选路径」这类复杂条件首版不做,靠 AI 判断兜底。

---

## 3. 清理项知识表(可清项 + 风险标记)

lemon 的 `recommend="NO"` ≈ 我们的 `risk=caution`(数据不可再生或需用户确认),`recommend="YES"` ≈ `recommend`。

### 3.1 系统垃圾

| 项 | 路径 | 深度 | 风险 |
|---|---|---|---|
| 系统缓存 | `/Library/Caches`(带 §1.1 排除) | 1 | recommend |
| 系统日志 | `/Library/Logs/`(排除 DiagnosticReports 目录本身)、`/Library/Logs/DiagnosticReports`、`/private/var/log/asl/`、`/private/var/log/DiagnosticMessages/`、`/private/var/log/cups/`、`/private/var/log/`(带 §2 日志条件)、`/private/var/db/diagnostics` | 0/1 | recommend |
| iOS 照片缓存 | `~/Pictures/iPod Photo Cache/`(带条件) | 1 | recommend |
| iOS 升级包 | `~/Library/iTunes/` 递归 `*.ipsw` | -1 | recommend |
| iOS 设备备份 | `~/Library/Application Support/MobileSync/Backup` | 1 | **caution** |
| 废纸篓 | `~/.Trash/`(含隐藏文件、清空目录) | 1 | **caution** |
| 下载 | `~/Downloads` | 1 | **caution** |

### 3.2 开发垃圾(Xcode / Sketch)

| 项 | 路径 | 风险 |
|---|---|---|
| Xcode app 缓存 | `~/Library/Caches/com.apple.dt.Xcode/` + **SystemTempDir 专用临时目录**(见 §4.1) | recommend |
| DerivedData | `~/Library/Developer/Xcode/DerivedData/`(App Store 版更保守:只清其中 `*.app` 产物) | recommend(沙盒版 caution) |
| Module Caches | `~/Library/Developer/Xcode/DerivedData/ModuleCache.noindex/` | caution |
| iOS Device Support | `~/Library/Developer/Xcode/iOS DeviceSupport/` | **caution** |
| macOS Device Support | `~/Library/Developer/Xcode/macOS DeviceSupport/` | **caution** |
| Archives | `~/Library/Developer/Xcode/Archives/` 递归 `*.xcarchive` | **caution**(发布归档,含 dSYM) |
| Device Logs | `~/Library/Developer/Xcode/iOS Device Logs/`、`DeviceLogs/` | caution |
| DocumentationCache | `~/Library/Developer/Xcode/DocumentationCache/` | caution |
| Simulator | `~/Library/Developer/CoreSimulator/` | **caution**(整个模拟器数据) |
| Simulator Runtimes | `/Library/Developer/CoreSimulator/Profiles/Runtimes/`(及 Volumes 内层) | **caution**(运行时镜像,重下很大) |
| Sketch 缓存/日志 | `~/Library/Caches/com.bohemiancoding.sketch3/`、`~/Library/Logs/com.bohemiancoding.sketch3/`、AS 下 `crash.log` | recommend |

### 3.3 浏览器缓存(精确到 Cache 子目录,绝不动整个 profile)

| 浏览器 | 只清这些 |
|---|---|
| Safari | `~/Library/Caches/com.apple.Safari/`、`~/Library/Caches/Metadata/Safari/`、`Containers/com.apple.Safari.CacheDeleteExtension/`、`Caches/com.apple.Safari.SafeBrowsing/`、`Caches/com.apple.safaridavclient/` |
| Chrome | 仅 `~/Library/Caches/Google/Chrome/Default/Cache/`(**不是** Chrome 目录整个) |
| Edge | 仅 `~/Library/Caches/Microsoft Edge/Default/Cache/` |
| Firefox | `~/Library/Caches/Firefox/` |
| QQ 浏览器 | 仅 `~/Library/Caches/QQBrowser2/Default/Cache/` |
| Opera | 按版本:`Caches/Opera/` 或 `Caches/com.operasoftware.Opera` + `AS/com.operasoftware.Opera/GPUCache` |

> 关键经验:浏览器只能清 `Default/Cache` 这类纯缓存子目录,profile 里混着书签/密码/扩展数据。

### 3.4 其他

| 项 | 路径 | 风险 |
|---|---|---|
| Mail 附件缓存 | `~/Library/Containers/com.apple.mail/Data/Library/Mail Downloads/` | **caution** |
| 下载隔离日志(隐私) | `~/Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2` | recommend |

---

## 4. 机制性知识(扫描器设计参考)

### 4.1 SystemTempDir:per-app 临时缓存目录

lemon 的 `path type="special" value="SystemTempDir" value1="<bundleid>"` 指向 **`/private/var/folders/<xx>/<hash>/C/<bundleid>`**(darwin per-user cache 目录,`getconf DARWIN_USER_CACHE_DIR` 可得)。每个 app 在这里还有一份缓存,常规 `~/Library/Caches` 扫描覆盖不到——**我们 v2 扫描来源的又一个盲区,已补入规格**。

### 4.2 卸载残留匹配(LemonUninstaller)

- 应用身份:`Info.plist` 的 bundleID(`kCFBundleIdentifierKey`)+ appName(`kCFBundleNameKey`,缺省用文件名)+ executableName + 显示名;
- 匹配:bundleID 精确/前缀 + 名称小写前缀双向启发;
- 厂商前缀保护:仍装有同厂商(`com.tencent.*`)其他应用时不判孤儿;
- pkg 软件:`pkgutil --pkgs / --files / --only-dirs` 取安装收据,卸载后 `sudo pkgutil --forget`;
- 别名特例表(`uninstall.xml`):如有道云笔记 → `com.youdao.YoudaoDict`、JetBrains Toolbox → AS 下 `Toolbox` 目录;
- 搜索目录集(LMSearchPath):`/Library` 与 `~/Library` 两级的 Application Support、Caches、Preferences、Saved Application State、Logs、Containers、LaunchAgents、LaunchDaemons、StartupItems、CrashReporter、DiagnosticReports、WebKit,另有 `/private/var/folders` 临时目录。

### 4.3 其他设计信号

- `recommend` / `fastmode` / `defaultstate` 三级开关:默认清、快速模式含不含、UI 默认勾选——对应我们的 risk 分级 + skill 判断准则;
- 真删前走 `movetrash`(废纸篓),与我们 v2 的 Trash 优先策略一致;
- 沙盒版规则整体比直发版**更保守**(如 DerivedData 只清 `*.app`),印证「同一路径在不同上下文风险不同」,AI 判断时应参考;
- 体积统计有缓存层(`QMScanFileSizeCacheManager`),大目录 du 是性能大头——已列入我们后续迭代。

---

## 5. 落地对照(实施时执行)

| 本文档内容 | 落到 clean-zd v2 的哪里 |
|---|---|
| §1.1、§1.2 | 引擎硬编码 safety 排除名单 |
| §1.3 | scan 排除名单 + 后续专项规则候补 |
| §1.4 | leftover 扫描器的排除逻辑 |
| §2 | rules.json 条件字段的种子用例 |
| §3 | rules.json 初始规则(与 Bash 转译合并,风险标记照搬) |
| §4.1 | scan 缓存类来源 + Xcode 规则的附加路径 |
| §4.2 | leftover 扫描器算法(已在规格) |
