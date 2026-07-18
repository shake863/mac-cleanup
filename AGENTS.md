# AGENTS.md

This file provides guidance to AI coding assistants (Claude Code, Codex, etc.) when working with code in this repository.

## What this is

A single-file macOS cleanup utility written in Bash. This is a personal fork of [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh), rebranded as `clean-zd`. The entire tool lives in the `clean-zd` script (~500 lines). `installer.sh` handles download/install/uninstall. There is no build system, no dependencies, and no test suite.

## Running & testing

```bash
./clean-zd            # run the cleanup for real (prompts for sudo)
./clean-zd -d         # dry-run: estimate reclaimable space, then prompt to continue
./clean-zd -v         # verbose (set -x) debug output
./clean-zd -u         # also run `brew update`/`brew upgrade`
./clean-zd -h         # help
```

There are no automated tests — validate changes by running with `-d` (dry-run) first, which is non-destructive. Use `shellcheck clean-zd` to lint (the script already carries `# shellcheck disable` directives).

## Architecture

The script has two execution paths controlled by the `dry_run` variable, and understanding this dual-path design is essential — nearly every cleanup block branches on it:

- **Real run** (`dry_run` unset): paths are deleted and CLI cache commands (`brew cleanup`, `npm cache clean`, `docker system prune`, etc.) are executed.
- **Dry-run** (`-d`): paths are only *collected*, their size summed via `count_dry`, reported through `bytesToHuman`, and then the script re-`exec`s itself without `-d` if the user confirms.

### Core helper functions (defined at top of `clean-zd`)

- `collect_paths <path...>` — appends to the global `path_list` array. This is the primary mechanism: you register paths, then act on them.
- `remove_paths` — deletes everything in `path_list` (only when not a dry-run), then unsets the array.
- `count_dry` — sums sizes of `path_list` entries into `dry_results` (dry-run accounting).
- `bytesToHuman` — formats byte counts; message wording changes based on whether it's a dry-run.
- `msg` / `die` — logging; `msg` suppresses output during dry-run.
- `deleteCaches` — an older standalone helper (largely superseded by the collect/remove pattern).

### The standard cleanup block pattern

Most cleanups follow this shape and this is the pattern to replicate when adding new ones:

```bash
if [ -d ~/Some/App/Cache ]; then      # guard: only if the target exists
  collect_paths ~/Some/App/Cache/*    # register paths
  msg 'Clearing Some App cache...'    # user-facing message
  remove_paths                        # delete (respects dry-run)
fi
```

For tools with their own cache-clearing command, branch on `dry_run` explicitly: run the command in the real path, and `collect_paths` the cache directory in the dry-run path (see the `npm`/`yarn`/`go`/`composer` blocks).

### Space accounting

At start the script records `oldAvailable` from `df /`; at the end it diffs against `newAvailable` to report actual space freed. Dry-run instead relies on the `dry_results` sum.

## Release process

Pushing a git tag triggers `.github/workflows/release.yml`, which bumps the Homebrew formula in `shake863/homebrew-tap` (the tap repo must be created separately for this to work). No manual release steps.

## Dev-log

每次完成一项开发任务时,在 `docs/dev-log/YYYY-MM-DD-<主题>.md` 新建一份 dev-log,随代码一起提交。用中文写,涵盖:背景/目标、改动内容、验证方式、遗留/后续、相关文档或提交。以 `docs/dev-log/2026-07-18-rebrand-clean-zd.md` 为格式参考。目的是让每次改动可追踪。

## Notes for editing

- This is a detached fork of `mac-cleanup/mac-cleanup-sh` (upstream is inactive; no further syncing). All install/reference URLs point at `shake863/mac-cleanup` on the `master` branch. Only the Credits/CHANGELOG retain upstream links for attribution.
- The script contains customizations not in upstream (`conda clean`, Tencent Meeting / extra Xcode / Application Support cache cleanups around lines 315–346). These now follow the guarded collect/remove pattern (or a `type`+`dry_run` guard for command-based tools like conda) — keep it that way; `-d` dry-run must stay non-destructive.

本项目启用多智能体黑板协作(multi-ai)。你是 codex,启动时必须先读取并遵循 `.agent_workspace/roles/codex.md`。
