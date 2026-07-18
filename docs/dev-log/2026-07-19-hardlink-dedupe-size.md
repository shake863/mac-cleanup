# 2026-07-19 体积统计对硬链接去重

## 背景 / 目标

上一个修复（f366ebd）把体积统计从 `st_size` 改为 `st_blocks * 512` 后，仍有一类虚高：`path_size()` 目录遍历按路径累加，硬链接到同一 inode 的文件会被重复计入。conda 用硬链接在 `pkgs/` 与各环境间共享包文件，实测 `~/anaconda3` 被 `clean-zd analyze` 报为 16GB，而 `du -sh` 为 11GB。目标是与 `du` 同口径：同一 inode 只计一次。

## 改动内容

- `cleanzd/paths.py` `path_size()`：目录遍历中对 `st_nlink > 1` 的文件按 `(st_dev, st_ino)` 去重，重复出现的 inode 跳过不累加。`st_nlink == 1` 的普通文件不进集合，避免大目录下无谓的内存开销。
- `tests/test_paths.py`：新增 `test_hardlinked_file_counted_once`——在临时目录创建 1 个文件加 2 个跨子目录硬链接，断言 `path_size` 只计一次物理占用（TDD：修复前失败于 12288 != 4096）。

## 验证

- 全量测试：`python3 -m unittest discover -s tests`，91 个用例全部通过。
- 实测：`path_size(~/anaconda3)` 报 11.0GB，与 `du -sh ~/anaconda3` 的 11G 一致（修复前 16GB）。

## 遗留 / 后续

- 去重集合以整个 `path_size(path)` 调用为界；若上层分别对两个目录调用再求和（如 analyze 按子目录分层统计），跨目录硬链接仍会各计一次。`du` 对多个参数是全局去重，目前 analyze 单层占比场景影响很小，暂不处理。

## 相关文档 / 提交

- 前置修复：f366ebd（稀疏文件按 `st_blocks` 统计物理占用）
- `CHANGELOG.md` 定制改动一节同步补充
