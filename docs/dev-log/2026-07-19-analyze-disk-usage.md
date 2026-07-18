# 2026-07-19 磁盘占比分析(analyze 子命令)

## 背景 / 目标

用户需求(参考 lemon-cleaner):增加磁盘占比分析能力,识别开发遗留大目录——GitHub 项目编译产物、node_modules、Python venv/conda 环境等"一次使用、永久占用"的目录,给出可删除/可优化/有价值的建议。交互铁律:**不做全盘递归,一次只展开一个目录的一层,先定性、有价值再下探**。

该需求 7-19 凌晨曾以 task_20260719_02 走黑板评审流程(误触协同,已作废、零代码)。本次由用户直接重提,按其中 V1 设计草案直接实施,四个开放问题拍板如下:

1. **体积缓存**:首版不做。靠 `--top`/`--min-size` 控制输出,单层 du 的耗时(大目录数十秒)可接受;缓存留待有实际痛点再加(对应 lemon 的 `QMScanFileSizeCacheManager`,见知识文档 §性能)。
2. **签名表位置**:独立内置常量(`cleanzd/analyze.py` 内),不进 rules.json——语义是"识别知识"而非"清理规则",首版不做用户可配。
3. **age_days 语义**:签名命中时改用项目锚点 mtime(兄弟 `.git/HEAD` 或 marker 文件,取最新);`dev-project` 自身也取其 `.git/HEAD`。目录自身 mtime 仅作兜底。
4. **与 scan dev 类别的关系**:保留双入口。`scan`(主动候选推送,全局已知路径)+ `analyze`(交互式追问,项目内产物),互不吸收。

## 改动内容

- 新增 `cleanzd/analyze.py`:
  - `run_analyze(dir, top, min_size_mb, home)`:只读展开一层,输出每个子项 `size / percent / kind / signature / rebuildable / age_days / hint`,附 `total` 与被省略项汇总;
  - 签名表(带兄弟 marker 锚防误伤):node_modules、cargo-target、gradle-build、js-build、python-venv(pyvenv.cfg 或名称+bin/python)、conda-env;
  - `classify_kind`:dev-project(含项目 marker)/ cache(~/Library/Caches)/ app-data(~/Library 其余)/ user-data(Documents 等标准目录)/ unknown;
  - 边界:目标必须在 $HOME 内(允许 $HOME 本身,因只读)、拒绝不存在/非目录/软链逃逸、目录不可读报 `AnalyzeError` 而非崩溃。
- `cleanzd/__main__.py`:新增 `analyze [DIR] [--json] [--top N] [--min-size MB]` 子命令(默认 `~`、top 20、10MB)。
- `tests/test_analyze.py`:25 个用例——签名命中与误伤防护(如无 package.json 的 build 目录不算产物)、kind 分类、占比/排序/省略汇总、锚点年龄(node_modules 用 package.json、dev-project 用 .git/HEAD)、家目录边界与软链逃逸、无权限容错、渲染与 CLI。
- market-zd 仓库 `zd-toolkit/mac-clean` skill 升至 0.2.0:新增「占比分析模式」工作流(analyze → 逐项定性 → 有价值再下探 → 触底汇总三类建议 → 删除决定经 manifest+clean),analyze 本身零删除能力,dev-artifact 一律 caution 逐项问用户。

## 验证方式

- `python3 -m unittest discover -s tests`:89 个测试全绿(TDD:每个行为先看到失败再实现)。
- 真实只读验证:
  - `clean-zd analyze ~/github --top 10 --min-size 50`:47.5GB 总量,识别出 974 天未动的 4.4GB 项目;
  - `clean-zd analyze ~/github/cherry-studio`:命中 node_modules(2.2GB / 78.3%,rebuildable)与 js-build(out,66.8MB),年龄取自项目锚点。

## 遗留 / 后续

- 体积缓存 / `--fast` 估算模式:大目录(如 `~/Library`)单次统计仍慢,待有痛点再做。
- 签名表可按需扩充(如 .gradle caches、Pods、DerivedData 项目内形态);扩充须带误伤防护用例。
- skill 侧建议对"命令类优化"(docker prune、git gc)只建议不代执行,后续可评估纳入引擎命令规则。

## 相关文档 / 提交

- 设计草案留档:`.agent_workspace/tasks/task_20260719_02.md`(已作废任务,仅历史参考)。
- 知识出处:`docs/reference/lemon-cleaner-knowledge.md`(体积统计缓存层一节)。
- market-zd 仓库同日提交:mac-clean skill 0.2.0。
