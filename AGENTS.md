# AGENTS.md

This file provides guidance to AI coding assistants (Claude Code, Codex, etc.) when working with code in this repository.

## What this is

`clean-zd` is a Python 3.9+ macOS cleanup engine with no third-party runtime dependencies. It was originally forked from [mac-cleanup/mac-cleanup-sh](https://github.com/mac-cleanup/mac-cleanup-sh), but the legacy Bash implementation is retired. The current product is an AI-driven scan/manifest/clean/status workflow with a deterministic, safety-guarded execution layer.

## Running & testing

```bash
python3 -m unittest discover -s tests -v  # full test suite
./clean-zd status                         # manifest/history summary
./clean-zd scan                           # read-only candidate scan
./clean-zd scan --json                    # structured output for AI
./clean-zd clean --dry-run                # non-destructive estimate
./clean-zd clean --dry-run --include-caution
```

Tests must never touch real user data. Set `CLEAN_ZD_CONFIG_DIR` to a temporary directory for config tests and build all test file trees under temporary paths. Real verification may run `scan` and `clean --dry-run`; never run a real clean merely as a test.

## Architecture

The product has three layers:

- **Execution layer** (`cleanzd/`): deterministic Python CLI; contains no AI.
- **Knowledge layer** (`cleanzd/rules.json` plus `~/.config/clean-zd/`): built-in rules, local manifest, ignore list, and history.
- **Intelligence layer** (external skill): asks the engine to scan, reasons about candidates, records decisions, and requests user confirmation before cleaning.

Key modules:

- `cleanzd/__main__.py`: argparse CLI dispatch for `scan`, `manifest`, `clean`, and `status`.
- `cleanzd/paths.py`: config directory, path expansion, size accounting, human-readable sizes.
- `cleanzd/safety.py`: hardcoded exclusions and `validate_target`; this is a security boundary.
- `cleanzd/config.py`: manifest and ignore persistence.
- `cleanzd/rules.py` / `cleanzd/rules.json`: rule models, loading, and target evaluation.
- `cleanzd/clean.py`: dry-run, Trash-first disposal, command rules, history, and manifest lifecycle.
- `cleanzd/scan/`: candidate orchestration and category scanners.
- `tests/`: stdlib `unittest` coverage.

## Safety invariants

- AI never deletes files directly. It may only write manifest/ignore decisions through the CLI.
- The engine never deletes outside `$HOME`.
- Reject roots, `$HOME` itself, missing paths, bare globs, safety-list hits, and symlink escapes.
- Re-run `validate_target` immediately before accepting a manifest or rule target for cleanup.
- Default disposal moves targets to `~/.Trash`; `--purge` is the only direct-delete path.
- `risk=caution` is skipped unless `--include-caution` is explicit.
- Scans are read-only and leftovers are always conservative `caution` candidates.
- Permission-denied paths must be skipped without aborting an entire scan or dry-run.

Changes to safety behavior require a failing regression test first and must stay grounded in `docs/reference/lemon-cleaner-knowledge.md`.

## Rules schema

`rules.json` contains:

- **Path rules**: `id`, `title`, `tips`, `risk`, `strategy`, `paths`; optional `depth`, `match`, `exclude`, `min_size`, `older_than_days`.
- **Command rules**: `id`, `title`, `tips`, `command`, `guard`; optional `risk`, `dry_paths`.
- **Aliases**: installed bundle IDs mapped to data-directory names for conservative leftover matching.

When translating or changing rules, compare against the retired Bash behavior documented in `docs/dev-log/2026-07-18-v2-python-rewrite.md` and the lemon knowledge reference. Add a rule-data regression test for every omission found during comparison.

## Dev-log

每次完成一项开发任务时,在 `docs/dev-log/YYYY-MM-DD-<主题>.md` 新建一份 dev-log,随代码一起提交。用中文写,涵盖:背景/目标、改动内容、验证方式、遗留/后续、相关文档或提交。以 `docs/dev-log/2026-07-18-rebrand-clean-zd.md` 为格式参考。目的是让每次改动可追踪。

## Notes for editing

- Python modules must remain standard-library only and compatible with Python 3.9. Use `from __future__ import annotations` when modern annotations require it.
- User-visible CLI output is Chinese.
- Preserve the separation between deterministic execution, JSON knowledge, and external AI workflow.
- Do not broaden safety or leftover heuristics without evidence, tests, and documentation.
- Older specs and plans remain historical records; do not rewrite them merely because the implementation has advanced.

本项目启用多智能体黑板协作(multi-ai)。你是 codex,启动时必须先读取并遵循 `.agent_workspace/roles/codex.md`。
