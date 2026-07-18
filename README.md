# clean-zd

AI 驱动的 Mac 清理助手引擎。它负责确定性扫描、清单管理和安全清理；AI 负责判断候选项，但永远不能绕过引擎直接删除文件。

## 特点

- Python 3.9+，仅使用标准库，无第三方运行时依赖。
- `scan → manifest → clean → status` 完整闭环。
- 默认移入废纸篓；只有显式 `--purge` 才直接删除。
- `risk=caution` 默认跳过；只有显式 `--include-caution` 才纳入。
- 硬编码 safety 排除名单、家目录边界和软链逃逸校验。
- 内置通用 `rules.json`，本机决定保存在 `~/.config/clean-zd/`。

## 安装

克隆仓库后可以直接运行：

```bash
git clone https://github.com/shake863/mac-cleanup.git
cd mac-cleanup
./clean-zd --help
```

也可以建立全局命令软链：

```bash
ln -s "$PWD/clean-zd" /usr/local/bin/clean-zd
```

如果 `/usr/local/bin` 不可写，请为 `ln` 增加 `sudo`，或链接到你自己的 `PATH` 目录。

## 使用

### 1. 扫描候选

扫描只读，永不删除：

```bash
./clean-zd scan
./clean-zd scan --category cache --category dev
./clean-zd scan --json
```

支持类别：`cache`、`dev`、`leftover`、`bigfile`、`system`。卸载残留和系统项只作为候选，需人工或 AI 复核。

### 2. 管理本机清单

```bash
./clean-zd manifest add ~/Library/Caches/example \
  --strategy empty-dir \
  --reason "可再生缓存"

./clean-zd manifest ignore ~/Library/Caches/keep-me \
  --reason "需要保留"

./clean-zd manifest list
```

`manifest add` 会执行硬安全校验；根目录、家目录本身、家目录外路径、裸 glob、软链逃逸和 safety 名单目标都会被拒绝。

### 3. 预览与清理

始终先运行 dry-run：

```bash
./clean-zd clean --dry-run
./clean-zd clean --dry-run --include-caution
```

确认后执行清理：

```bash
./clean-zd clean
```

默认把文件移入 `~/.Trash`。只有明确不需要恢复时才使用：

```bash
./clean-zd clean --purge
```

### 4. 查看状态

```bash
./clean-zd status
```

状态包含 manifest/ignore 数量、上次清理和累计释放空间。

## 与 AI skill 配合

完整工作流由 AI skill 驱动：

1. 调用 `clean-zd scan --json` 获取新候选。
2. AI 对可再生缓存给出判断和理由；删除类及 `caution` 项必须询问用户。
3. 将结论写入 manifest 或 ignore。
4. 展示 `clean --dry-run` 结果，用户确认后才调用 `clean`。
5. 有普适价值的本机结论再沉淀到仓库 `rules.json`。

安全边界始终不变：AI 只能写清单，真正删除只能发生在 `clean-zd clean` 内部。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
./clean-zd status
./clean-zd scan --category cache
./clean-zd clean --dry-run
```

设计与实施文档位于 `docs/superpowers/`，规则知识来源见 `docs/reference/lemon-cleaner-knowledge.md`。

## Credits

本项目最初 fork 自 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh)，感谢原作者及所有贡献者。

安全排除、条件规则和扫描机制参考并人工提炼自 [Tencent/lemon-cleaner](https://github.com/Tencent/lemon-cleaner) 的公开知识；未复制其 GPL 规则实现。
