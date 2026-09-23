# 2026-09-23 缓存扫描移除 DARWIN_USER_CACHE_DIR 来源

## 背景 / 目标

T8 把 darwin per-app 临时缓存目录(`getconf DARWIN_USER_CACHE_DIR`,即 `/var/folders/<xx>/<hash>/C/<bundle-id>`,lemon 的 SystemTempDir)加进了缓存扫描来源,候选标为 `cache / recommend / empty-dir`。

但 `/var` 是指向 `/private/var` 的软链,resolve 后落在 `$HOME` 之外,`validate_target` 必然拒绝:`clean-zd manifest add` 一律报「拒绝写入: 路径不在家目录内(或经软链逃逸)」。扫描建议清、清单拒绝登记,两层行为自相矛盾。2026-09-23 在 macmini 上产生了 76 个无法登记的候选(约 1GB),每次扫描都会重复出现。

需要二选一统一行为:

- A:扫描不再产出这类候选;
- B:安全校验对当前用户自己的 `DARWIN_USER_CACHE_DIR` 开例外。

## 决策:选 A

- 安全模型最简单:「引擎从不在 `$HOME` 之外删除」这条不变式保持原样,不需要在 `validate_target` 这一安全边界里加任何例外、也不需要依赖 `getconf` 输出做信任判断。
- B 要引入第二个可删除根,并且 `validate_target`、`clean` 执行前复核、`analyze` 的家目录检查都得同步改,扩大了安全面,收益只是约 1GB 由系统自己会回收的临时缓存。
- macOS 会自行回收 `/var/folders/.../C`(重启 / 系统清理),不需要本工具介入。

## 改动内容

- `cleanzd/scan/cache.py`:移除 `_darwin_cache_dir()` 以及对 `DARWIN_USER_CACHE_DIR` 的扫描,留一行注释说明原因。
- `tests/test_scan.py`:新增 `test_scan_skips_darwin_user_cache_dir` 回归测试(伪造 `getconf` 返回一个含 2MB 子目录的临时目录,断言 `cache.scan()` 不产出其下候选)。先写测试确认失败,再改实现。
- `safety.py` 的 `SAFETY_COMPONENT_GLOBS` 保留不动:它按路径组件匹配,对其他位置同样生效,属于纵深防御。
- `docs/reference/lemon-cleaner-knowledge.md` §4.1 追加更新说明;`CHANGELOG.md` 追加一条。

## 验证方式

- 改动前:`python3 -m unittest discover -s tests` → 91 个测试 OK。
- 新测试改实现前失败,改后 `python3 -m unittest discover -s tests` → 92 个测试 OK。
- 真实只读验证(M1 Mini):用旧逻辑对 `DARWIN_USER_CACHE_DIR` 跑 `_scan_roots` + `_admit`,得到 76 个候选 / 854MB,复现问题;修复后 `./clean-zd scan --category cache --json` 中 `/var/folders` 候选为 0。
- `manifest ignore` 不做 `validate_target`,用临时 `CLEAN_ZD_CONFIG_DIR` 验证过可以写入 `/var/folders/...` 路径;既然扫描不再产出,这一点只对历史条目有意义。
- 未运行 `clean-zd clean`(不做任何删除)。

## 遗留 / 后续

- 历史上若有 `/var/folders/...` 已写入 ignore 名单,现在已无作用,可留可删。
- 若将来确实要清理这类目录,应走 B 方案,并先补安全回归测试和文档依据。

## 相关文档或提交

- 引入该来源的提交:T8 `7ecf3d6`
- safety 相关:`docs/dev-log/2026-07-18-system-temp-safety.md`
- 知识来源:`docs/reference/lemon-cleaner-knowledge.md` §4.1
