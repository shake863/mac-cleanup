# clean-zd 改造实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 fork `shake863/mac-cleanup` 改造成独立工具 `clean-zd`，所有引用指向自己的 fork，移除原作者专属流程。

**Architecture:** 纯 rebrand + 重命名任务，涉及 4 个文件（可执行脚本、installer、README、release workflow）+ CHANGELOG。无运行时逻辑改动（除一处 bug 修复）。验证靠 `shellcheck`、`./clean-zd -d` dry-run、以及 `grep` 残留扫描，而非单元测试。

**Tech Stack:** Bash、GitHub Actions、Markdown、shellcheck。

## Global Constraints

- 命令名 / 可执行文件名 / 安装名统一为 `clean-zd`（verbatim）。
- fork 地址：`https://github.com/shake863/mac-cleanup`，raw 分支为 `master`（上游是 `main`，替换时务必改成 `master`）。
- Homebrew：tap = `shake863/homebrew-tap`，formula 名 = `clean-zd`（用户将来自建 tap 仓库）。
- LICENSE 原作者版权行**不得改动**（MIT 法律要求）。
- 清理业务逻辑不动；仅允许修改第 210 行硬编码路径这一个 bug。
- 用 `git mv` 保留重命名历史；提交粒度小、信息用中文。

---

### Task 1: 重命名可执行脚本并更新脚本内引用

**Files:**
- Rename: `mac-cleanup` → `clean-zd`（`git mv`）
- Modify: `clean-zd`（原 17-18、134、210 行）

**Interfaces:**
- Produces: 可执行文件 `clean-zd`，供 installer 与 README 引用；命令名由 `basename` 动态得出。

- [ ] **Step 1: 用 git mv 重命名文件**

```bash
git mv mac-cleanup clean-zd
```

- [ ] **Step 2: 更新 usage() 署名与项目 URL（原 17-18 行）**

把：
```
A Mac Cleaning up Utility by fwartner
https://github.com/mac-cleanup/mac-cleanup-sh
```
改成：
```
A Mac Cleaning up Utility (clean-zd)
https://github.com/shake863/mac-cleanup
```

- [ ] **Step 3: 更新 keep-alive 注释（原 134 行）**

把 `# Keep-alive sudo until \`mac-cleanup.sh\` has finished` 改为
`# Keep-alive sudo until \`clean-zd\` has finished`

- [ ] **Step 4: 修复第 210 行硬编码路径 bug**

把：
```
    collect_paths /Users/wah/Library/Developer/CoreSimulator/Devices/*/data/Library/!(PreferencesCaches|Caches|AddressBook)
```
改成（与上一行 209 保持同样的 `~/` 家目录写法）：
```
    collect_paths ~/Library/Developer/CoreSimulator/Devices/*/data/Library/!(PreferencesCaches|Caches|AddressBook)
```

- [ ] **Step 5: shellcheck 验证无新增问题**

Run: `shellcheck clean-zd`
Expected: 退出码 0，或仅剩改造前已存在的告警（无新增 error）。

- [ ] **Step 6: dry-run 验证脚本可执行、帮助文本正确**

Run: `./clean-zd -h`
Expected: 帮助文本首行程序名显示为 `clean-zd`，署名行显示 `(clean-zd)` 与 `github.com/shake863/mac-cleanup`。

- [ ] **Step 7: 确认脚本内无残留上游引用**

Run: `grep -n 'fwartner\|mac-cleanup-sh\|/wah/\|mac-cleanup.sh' clean-zd`
Expected: 无输出（退出码 1）。

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor: 重命名 mac-cleanup 为 clean-zd 并修复硬编码路径"
```

---

### Task 2: 改造 installer.sh 指向 fork

**Files:**
- Modify: `installer.sh`（11、51、53、55、61 行）

**Interfaces:**
- Consumes: Task 1 产出的 `clean-zd` 文件名（raw 地址与安装名需一致）。

- [ ] **Step 1: 更新 usage 项目链接（11 行）**

把 `Installer of Mac Cleanup (https://github.com/fwartner/mac-cleanup)` 改为
`Installer of clean-zd (https://github.com/shake863/mac-cleanup)`

- [ ] **Step 2: 更新 install() 的下载地址与文件名（51 行）**

把：
```
    curl -o mac-cleanup https://raw.githubusercontent.com/mac-cleanup/mac-cleanup-sh/main/mac-cleanup
```
改成：
```
    curl -o clean-zd https://raw.githubusercontent.com/shake863/mac-cleanup/master/clean-zd
```

- [ ] **Step 3: 更新 chmod 与安装目标（53、55 行）**

把 `chmod +x mac-cleanup` 改为 `chmod +x clean-zd`；
把 `sudo mv mac-cleanup /usr/local/bin/mac-cleanup` 改为 `sudo mv clean-zd /usr/local/bin/clean-zd`。

- [ ] **Step 4: 更新 uninstall() 目标（61 行）**

把 `sudo rm /usr/local/bin/mac-cleanup` 改为 `sudo rm /usr/local/bin/clean-zd`。

- [ ] **Step 5: shellcheck 验证**

Run: `shellcheck installer.sh`
Expected: 退出码 0，无新增 error。

- [ ] **Step 6: 确认无残留上游引用**

Run: `grep -n 'fwartner\|mac-cleanup-sh\|/mac-cleanup\b' installer.sh`
Expected: 无输出。

- [ ] **Step 7: Commit**

```bash
git add installer.sh
git commit -m "refactor: installer 指向 shake863 fork 与 clean-zd"
```

---

### Task 3: 改造 README.md

**Files:**
- Modify: `README.md`（标题、安装/更新/卸载章节、Usage、Contributors）

**Interfaces:**
- Consumes: `clean-zd` 命令名、fork 地址、`master` 分支、`shake863/homebrew-tap`。

- [ ] **Step 1: 更新标题（1 行）**

把 `# mac-cleanup` 改为 `# clean-zd`。

- [ ] **Step 2: 更新 Homebrew 安装段（52-69 行区域）**

把 tap 与 formula 改为你的，并在 `### Using homebrew` 标题下加一行说明：
```
> 需先自建 `shake863/homebrew-tap` 仓库后此方式才生效。
```
`brew tap fwartner/tap` → `brew tap shake863/tap`
`brew install fwartner/tap/mac-cleanup` → `brew install shake863/tap/clean-zd`
`brew edit fwartner/tap/mac-cleanup` → `brew edit shake863/tap/clean-zd`
`brew install fwartner/tap/mac-cleanup`（69 行）→ `brew install shake863/tap/clean-zd`

- [ ] **Step 3: 更新 curl/wget 安装地址（77、83 行）**

把两处 `mac-cleanup/mac-cleanup-sh/main/installer.sh` 改为 `shake863/mac-cleanup/master/installer.sh`。

- [ ] **Step 4: 更新 Step by Step 手动安装段（88-93 行）**

- 88 行：`curl -o cleanup https://raw.githubusercontent.com/mac-cleanup/mac-cleanup-sh/main/mac-cleanup` → `curl -o clean-zd https://raw.githubusercontent.com/shake863/mac-cleanup/master/clean-zd`
- 89 行：`chmod +x cleanup` → `chmod +x clean-zd`
- 90 行：`sudo mv cleanup /usr/local/bin/cleanup` → `sudo mv clean-zd /usr/local/bin/clean-zd`
- 93 行：`If installing with curl you need to call \`cleanup\` instead of \`mac-cleanup\`.` → 删除此行（命令名已统一为 clean-zd，不再有歧义）。

- [ ] **Step 5: 更新 Update / Uninstall 章节的 4 处 installer 地址（100、106、114、120 行）**

把每处 `mac-cleanup/mac-cleanup-sh/main/installer.sh` 改为 `shake863/mac-cleanup/master/installer.sh`。

- [ ] **Step 6: 更新 Usage Options 帮助示例（128、130-131、134 行）**

- 128 行：`$ mac-cleanup -h` → `$ clean-zd -h`
- 130 行：`A Mac Cleanup Utility by fwartner` → `A Mac Cleaning up Utility (clean-zd)`
- 131 行：`https://github.com/mac-cleanup/mac-cleanup-sh` → `https://github.com/shake863/mac-cleanup`
- 134 行：` mac-cleanup [FLAGS]` → ` clean-zd [FLAGS]`

- [ ] **Step 7: 精简 Contributors 段（143-161 行）**

用以下内容替换 143-161 行整段（去掉 opencollective/sponsors 原作者专属内容，保留致谢上游）：
```markdown
## Credits

本项目 fork 自 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh)，在其基础上做了个人定制（conda / pnpm / 腾讯会议缓存清理等）。感谢原作者及所有贡献者。
```

- [ ] **Step 8: 确认无残留上游引用**

Run: `grep -n 'fwartner\|mac-cleanup-sh\|opencollective\|/main/' README.md`
Expected: 无输出。

- [ ] **Step 9: Commit**

```bash
git add README.md
git commit -m "docs: README 全面指向 clean-zd 与 shake863 fork"
```

---

### Task 4: 改造 release workflow 并补 CHANGELOG

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `clean-zd` formula 名、`shake863/homebrew-tap`、`master` 分支。

- [ ] **Step 1: 改 homebrew job 并删除 tweet job**

用以下内容替换 `.github/workflows/release.yml` 全文：
```yaml
name: Release

on:
  push:
    tags:
      - "*"

jobs:
  homebrew:
    name: Bump Homebrew formula
    runs-on: ubuntu-latest
    steps:
      - name: Extract version
        id: extract-version
        run: |
          printf "::set-output name=%s::%s\n" tag-name "${GITHUB_REF#refs/tags/}"
      - uses: mislav/bump-homebrew-formula-action@v1
        if: "!contains(github.ref, '-')"
        with:
          formula-name: clean-zd
          formula-path: Formula/clean-zd.rb
          homebrew-tap: shake863/homebrew-tap
          base-branch: master
          commit-message: |
            {{formulaName}} {{version}}
        env:
          COMMITTER_TOKEN: ${{ secrets.HOMEBREW_TAP_GITHUB_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.HOMEBREW_TAP_GITHUB_TOKEN }}
```

- [ ] **Step 2: 写 CHANGELOG 初始条目**

把当前空的 `CHANGELOG.md` 写为：
```markdown
# Changelog

## clean-zd

本项目 fork 自 [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh)。

### 定制改动
- 重命名工具为 `clean-zd`，所有安装/引用指向 `shake863/mac-cleanup` fork。
- 新增 conda、pnpm、腾讯会议、额外 Xcode 与 Application Support 缓存清理。
- 修复上游遗留的硬编码模拟器路径（`/Users/wah/...` → `~/`）。
- 移除原作者专属的发推与 opencollective 内容。
```

- [ ] **Step 3: 校验 YAML 语法**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml')); print('YAML OK')"`
Expected: 输出 `YAML OK`。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml CHANGELOG.md
git commit -m "ci: release workflow 指向 clean-zd，移除发推;补 CHANGELOG"
```

---

### Task 5: 全仓库残留扫描与最终 dry-run

**Files:** 无修改（验收任务）

- [ ] **Step 1: 全仓库扫描上游引用（排除 LICENSE 与 spec/plan 文档）**

Run:
```bash
grep -rn 'fwartner\|mac-cleanup-sh\|/wah/' . \
  --exclude-dir=.git \
  --exclude=LICENSE \
  --exclude-dir=docs
```
Expected: 无输出。若有残留，回到对应文件修复后重跑。

- [ ] **Step 2: 确认旧文件名已不存在**

Run: `test ! -e mac-cleanup && echo "renamed OK"`
Expected: 输出 `renamed OK`。

- [ ] **Step 3: 最终 dry-run 冒烟测试**

Run: `./clean-zd -d`（在提示 `Continue? [enter]` 处按 Ctrl-C 中断，不实际执行删除）
Expected: 脚本正常运行到统计空间并给出 `Approx ... will be cleaned up`，无报错、无 `wah` 相关路径错误。

- [ ] **Step 4: 确认工作树干净**

Run: `git status --short`
Expected: 无输出（所有改动已提交）。

---

## Self-Review

**Spec coverage:**
- 脚本重命名 + usage/注释/210 行 → Task 1 ✅
- installer 三处地址/名称 → Task 2 ✅
- README 全部安装方式 + Homebrew 标注 + Contributors → Task 3 ✅
- release workflow 删推 + Homebrew 改指向 → Task 4 ✅
- CHANGELOG 初始条目 → Task 4 ✅
- LICENSE 不动 → Global Constraints 明确，无任务改它 ✅
- 验证（shellcheck / dry-run / grep）→ 各 Task 步骤 + Task 5 ✅

**Placeholder scan:** 无 TBD/TODO；每个改动步骤都给出精确原文与替换后文本。

**一致性:** 命令名、fork 地址、`master` 分支、`shake863/homebrew-tap`、formula 名 `clean-zd` 在所有任务中一致。
