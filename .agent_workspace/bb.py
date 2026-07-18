#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb.py — 共享黑板操作脚本(blackboard)

多智能体协同开发约定(共享黑板模式)的唯一状态写入通道。
Agent 对 state.json 的一切修改必须通过本脚本完成,禁止直接编辑;
任务书正文、留言正文仍由 Agent 直接编写 Markdown 文件。

仅用 Python3 标准库,零依赖。用法概览: python3 .agent_workspace/bb.py --help
"""

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

WS = Path(__file__).resolve().parent
STATE_FILE = WS / "state.json"
ARCHIVE_FILE = WS / "archive.json"
TASKS_DIR = WS / "tasks"
INBOX_DIR = WS / "inbox"

AGENTS = ["claude", "codex", "trae"]
STATUSES = ["pending", "working", "rework", "blocked", "done"]
RETRY_LIMIT = 3
READ_MARK = "[已读]"

TASK_TEMPLATE = """# {tid}:{title}

- 指派给:{assign}
- 发起者:{by}
- 类型:{type}
- 创建时间:{ts}

## 任务要求
{desc}

## 验收标准
(发起者补充:如何算完成)

## 执行记录
(执行者完成后在此追加:改动文件清单、测试结果、遗留问题)
"""


# ---------- 基础 ----------

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def die(msg):
    print(f"[bb] ✗ {msg}")
    sys.exit(1)


def ok(msg):
    print(f"[bb] ✓ {msg}")


def load_state():
    if not STATE_FILE.exists():
        die("state.json 不存在,黑板尚未初始化")
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"state.json 解析失败({e})。文件可能被改坏,请人类手工修复后重试")


def save_state(state):
    """原子写:临时文件 + rename,永不产生半截 JSON。"""
    data = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=WS, prefix=".state.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, STATE_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_archive():
    if not ARCHIVE_FILE.exists():
        return {"version": 1, "project": None, "archived": []}
    try:
        archive = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"archive.json 解析失败({e})。文件可能被改坏,请人类手工修复后重试")
    if not isinstance(archive, dict):
        die("archive.json 顶层必须是对象")
    if "archived" not in archive:
        archive["archived"] = []
    if not isinstance(archive.get("archived"), list):
        die("archive.json 字段 archived 必须是数组")
    archive.setdefault("version", 1)
    archive.setdefault("project", None)
    return archive


def save_archive(archive):
    """原子写 archive.json,与 state.json 使用不同临时文件前缀。"""
    data = json.dumps(archive, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=WS, prefix=".archive.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, ARCHIVE_FILE)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def archive_ids(archive):
    ids = set()
    for item in archive.get("archived", []):
        tid = item.get("id", "(无id)") if isinstance(item, dict) else "(非对象)"
        if tid in ids:
            die(f"归档 id 重复: {tid}")
        ids.add(tid)
    return ids


def check_agent(name):
    if name not in AGENTS:
        die(f"未知 agent「{name}」,必须是 {'/'.join(AGENTS)}")
    return name


def find_task(state, tid):
    for t in state.get("tasks", []):
        if t.get("id") == tid:
            return t
    die(f"看板上没有任务「{tid}」(用 status 查看现有任务)")


def touch(state, agent):
    state.setdefault("agents", {}).setdefault(agent, {})["last_active"] = now_iso()


def lock_of(state):
    return state.setdefault("lock", {"holder": None, "since": None})


def read_stdin_or(default):
    if not sys.stdin.isatty():
        body = sys.stdin.read().strip()
        if body:
            return body
    return default


def is_unread(path):
    try:
        head = path.read_text(encoding="utf-8")[:200]
        return READ_MARK not in head
    except OSError:
        return False


# ---------- 子命令 ----------

def cmd_status(args):
    me = check_agent(args.agent)
    state = load_state()
    lines = []
    lines.append(f"═══ 共享黑板 · {state.get('project', '?')} · 视角: {me} ═══")

    # 锁
    lock = state.get("lock") or {}
    holder = lock.get("holder")
    if holder is None:
        lines.append("锁: FREE")
    elif holder == me:
        lines.append(f"锁: 由你({me})持有,since {lock.get('since')} —— 可能是你上次未收尾,收尾后记得 done/unlock 释放")
    else:
        lines.append(f"⚠ 锁: 由 {holder} 持有,since {lock.get('since')}")
        lines.append(f"⚠ 防呆提醒:{holder} 可能尚未收尾。请先向人类确认是否继续;人类同意后你可正常 claim(claim 会要求先解锁或由人类处理)")

    # 任务总览
    tasks = state.get("tasks", [])
    counts = {s: 0 for s in STATUSES}
    for t in tasks:
        if t.get("status") in counts:
            counts[t["status"]] += 1
    lines.append("任务总览: " + "  ".join(f"{s}:{counts[s]}" for s in STATUSES) + f"  (共 {len(tasks)})")

    blocked = [t for t in tasks if t.get("status") == "blocked"]
    if blocked:
        lines.append("⚠ 挂起待人类裁决: " + ", ".join(t["id"] for t in blocked))

    # 我的任务
    mine_todo = [t for t in tasks if t.get("assigned_to") == me and t.get("status") in ("pending", "rework")]
    mine_doing = [t for t in tasks if t.get("assigned_to") == me and t.get("status") == "working"]
    if mine_doing:
        lines.append(f"你进行中的任务({len(mine_doing)}):")
        for t in mine_doing:
            lines.append(f"  · {t['id']} [{t.get('type', '-')}] {t.get('title', '')}  → 任务书: {t.get('file', '(未登记)')}")
    if mine_todo:
        lines.append(f"你的待办({len(mine_todo)}):")
        for t in mine_todo:
            retry = f" (retry {t.get('retry_count', 0)}/{RETRY_LIMIT})" if t.get("retry_count") else ""
            lines.append(f"  · {t['id']} [{t.get('status')}]{retry} {t.get('title', '')}  → 先 claim 再开工")
    if not mine_todo and not mine_doing:
        lines.append("你名下当前没有待办任务")

    # 收件箱
    my_inbox = INBOX_DIR / me
    msgs = sorted(my_inbox.glob("*.md")) if my_inbox.is_dir() else []
    unread = [m for m in msgs if is_unread(m)]
    if unread:
        lines.append(f"你的未读留言({len(unread)}):")
        for m in unread:
            lines.append(f"  · inbox/{me}/{m.name}  → 阅读后用 mark-read 标记")
    else:
        lines.append("收件箱: 无未读")

    print("\n".join(lines))


def cmd_claim(args):
    me = check_agent(args.agent)
    state = load_state()
    t = find_task(state, args.task_id)

    if t.get("assigned_to") != me:
        die(f"任务 {t['id']} 指派给的是「{t.get('assigned_to')}」,不是你({me})。如需转派,用 reassign 或请发起者处理")
    if t.get("status") not in ("pending", "rework"):
        die(f"任务 {t['id']} 当前状态为 {t.get('status')},只有 pending/rework 可领取")
    if int(t.get("retry_count", 0)) >= RETRY_LIMIT:
        t["status"] = "blocked"
        save_state(state)
        die(f"任务 {t['id']} 重试已达 {RETRY_LIMIT} 次上限,已自动置为 blocked,请人类裁决")

    lock = lock_of(state)
    if lock.get("holder") and lock["holder"] != me:
        die(f"锁由 {lock['holder']} 持有(since {lock.get('since')})。请先向人类确认:由对方收尾释放,或人类强制解锁(unlock --force)后再领取")

    lock["holder"] = me
    lock["since"] = now_iso()
    t["status"] = "working"
    touch(state, me)
    save_state(state)
    ok(f"{me} 已领取 {t['id']},状态 → working,锁已占用")
    if t.get("file"):
        print(f"[bb] 任务书: {t['file']} —— 请通读后按边界施工,完成后执行 done")


def cmd_done(args):
    me = check_agent(args.agent)
    state = load_state()
    t = find_task(state, args.task_id)
    if t.get("status") != "working":
        die(f"任务 {t['id']} 状态为 {t.get('status')},不是 working,无法标记完成")
    if t.get("assigned_to") != me:
        die(f"任务 {t['id']} 的执行者是 {t.get('assigned_to')},不是你({me})")

    t["status"] = "done"
    lock = lock_of(state)
    if lock.get("holder") == me:
        lock["holder"] = None
        lock["since"] = None
    touch(state, me)
    save_state(state)
    ok(f"任务 {t['id']} → done,锁已释放")
    print("[bb] 收尾清单:① 任务书「执行记录」已写? ② 需要 review/交接的话给对方 send 留言 ③ 向人类汇报并建议下一步由谁接手")


def cmd_set_status(args):
    me = check_agent(args.agent)
    state = load_state()
    t = find_task(state, args.task_id)
    to = args.status
    if to not in STATUSES:
        die(f"非法状态「{to}」,必须是 {'/'.join(STATUSES)}")

    note = ""
    if to == "rework":
        t["retry_count"] = int(t.get("retry_count", 0)) + 1
        if t["retry_count"] >= RETRY_LIMIT:
            to = "blocked"
            note = f"(第 {t['retry_count']} 次驳回,达到上限,自动转 blocked,请人类裁决)"
        else:
            note = f"(retry {t['retry_count']}/{RETRY_LIMIT})"

    old = t.get("status")
    t["status"] = to
    lock_note = ""
    if old == "working" and to != "working":
        lock = lock_of(state)
        if lock.get("holder") == t.get("assigned_to"):
            lock["holder"] = None
            lock["since"] = None
            lock_note = ",锁已释放"
    touch(state, me)
    save_state(state)
    ok(f"任务 {t['id']}: {old} → {to} {note}{lock_note}")
    if to == "rework":
        print(f"[bb] 请把驳回原因写进任务书,并给 {t.get('assigned_to')} send 留言")


def cmd_reassign(args):
    me = check_agent(args.agent)
    state = load_state()
    t = find_task(state, args.task_id)
    to = check_agent(args.to)
    old = t.get("assigned_to")
    t["assigned_to"] = to
    touch(state, me)
    save_state(state)
    ok(f"任务 {t['id']} 转派: {old} → {to}")


def cmd_add_task(args):
    me = check_agent(args.agent)
    assign = check_agent(args.assign)
    state = load_state()

    tid = args.id
    if tid:
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", tid):
            die("任务 id 只能包含字母/数字/下划线/连字符")
    else:
        stamp = datetime.now().strftime("%Y%m%d")
        n = 1
        existing = {t.get("id") for t in state.get("tasks", [])}
        while f"task_{stamp}_{n:02d}" in existing:
            n += 1
        tid = f"task_{stamp}_{n:02d}"

    if any(t.get("id") == tid for t in state.get("tasks", [])):
        die(f"任务 id「{tid}」已存在")

    TASKS_DIR.mkdir(exist_ok=True)
    task_path = TASKS_DIR / f"{tid}.md"
    if task_path.exists():
        die(f"任务书文件已存在: {task_path.name}")

    desc = args.desc or read_stdin_or("(发起者补充:具体要求与边界)")
    task_path.write_text(TASK_TEMPLATE.format(
        tid=tid, title=args.title, assign=assign, by=me,
        type=args.type, ts=now_iso(), desc=desc,
    ), encoding="utf-8")

    state.setdefault("tasks", []).append({
        "id": tid,
        "title": args.title,
        "assigned_to": assign,
        "type": args.type,
        "status": "pending",
        "retry_count": 0,
        "file": f"tasks/{tid}.md",
    })
    touch(state, me)
    save_state(state)
    ok(f"任务 {tid} 已登记,指派给 {assign},任务书: tasks/{tid}.md")
    print("[bb] 请检查任务书正文(任务要求/验收标准),必要时直接编辑补全")


def cmd_send(args):
    frm = check_agent(args.sender)
    to = check_agent(args.to)
    body = args.body or read_stdin_or(None)
    if not body:
        die("留言正文为空:用 --body 传入,或通过管道/stdin 输入")
    box = INBOX_DIR / to
    box.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"msg_{ts}_from_{frm}.md"
    (box / name).write_text(f"# {args.title}\n\n- 发件人:{frm}\n- 时间:{now_iso()}\n\n{body}\n", encoding="utf-8")

    state = load_state()
    touch(state, frm)
    save_state(state)
    ok(f"留言已投递: inbox/{to}/{name}")


def cmd_mark_read(args):
    me = check_agent(args.agent)
    box = INBOX_DIR / me
    if not box.is_dir():
        die(f"收件箱不存在: inbox/{me}/")
    targets = sorted(box.glob("*.md")) if args.all else [box / n for n in args.names]
    if not targets:
        die("没有指定要标记的留言(给出文件名,或用 --all)")
    marked = 0
    for p in targets:
        if not p.exists():
            print(f"[bb] ⚠ 跳过不存在的 {p.name}")
            continue
        text = p.read_text(encoding="utf-8")
        if READ_MARK in text[:200]:
            continue
        p.write_text(f"{READ_MARK} {now_iso()}\n{text}", encoding="utf-8")
        marked += 1
    ok(f"已标记 {marked} 条留言为已读")


def cmd_unlock(args):
    state = load_state()
    lock = lock_of(state)
    holder = lock.get("holder")
    if holder is None:
        ok("锁本来就是 FREE,无需操作")
        return
    if args.force:
        who = "人类(--force)"
    else:
        me = check_agent(args.agent or "")
        if holder != me:
            die(f"锁由 {holder} 持有,你({me})只能释放自己的锁。人类干预请用 unlock --force")
        who = me
        touch(state, me)
    lock["holder"] = None
    lock["since"] = None
    save_state(state)
    ok(f"锁已由 {who} 释放(原持有者: {holder})")


def cmd_archive(args):
    me = check_agent(args.agent)
    state = load_state()
    lock = lock_of(state)
    holder = lock.get("holder")
    if holder and holder != me:
        die(f"锁由 {holder} 持有(since {lock.get('since')})。请先确认对方已收尾或由人类解锁后再归档")

    archive = load_archive()
    existing_archive_ids = archive_ids(archive)
    tasks = state.get("tasks", [])
    by_id = {t.get("id"): t for t in tasks}

    if args.task_ids:
        candidates = []
        for tid in args.task_ids:
            t = by_id.get(tid)
            if not t:
                die(f"看板上没有任务「{tid}」(用 status 查看现有任务)")
            if t.get("status") != "done":
                die(f"任务 {tid} 当前状态为 {t.get('status')},不是 done,无法归档")
            candidates.append(t)
    else:
        candidates = [t for t in tasks if t.get("status") == "done"]

    if not candidates:
        touch(state, me)
        save_state(state)
        ok("没有可归档的 done 任务")
        return

    new_state = copy.deepcopy(state)
    new_archive = copy.deepcopy(archive)
    new_archive["version"] = new_archive.get("version") or 1
    new_archive["project"] = new_archive.get("project") or state.get("project")

    selected_ids = {t.get("id") for t in candidates}
    archived_new = 0
    skipped = 0
    repaired = 0
    archived_at = now_iso()
    for t in candidates:
        tid = t.get("id")
        if tid in existing_archive_ids:
            repaired += 1
            continue
        rec = copy.deepcopy(t)
        rec["archived_at"] = archived_at
        rec["archived_by"] = me
        new_archive.setdefault("archived", []).append(rec)
        existing_archive_ids.add(tid)
        archived_new += 1

    new_state["tasks"] = [t for t in new_state.get("tasks", []) if t.get("id") not in selected_ids]
    touch(new_state, me)

    save_archive(new_archive)
    save_state(new_state)
    ok(
        f"归档完成:新增 {archived_new} 个,跳过 {skipped} 个,修复 {repaired} 个; "
        f"archive: {ARCHIVE_FILE.relative_to(WS)}"
    )


def cmd_validate(_args):
    problems = []
    state = load_state()  # 解析失败会直接报错退出
    for key in ("project", "lock", "agents", "tasks"):
        if key not in state:
            problems.append(f"state.json 缺少顶层字段「{key}」")
    ids = set()
    for t in state.get("tasks", []):
        tid = t.get("id", "(无id)")
        if tid in ids:
            problems.append(f"任务 id 重复: {tid}")
        ids.add(tid)
        if t.get("status") not in STATUSES:
            problems.append(f"任务 {tid} 状态非法: {t.get('status')}")
        if t.get("assigned_to") not in AGENTS:
            problems.append(f"任务 {tid} 指派对象非法: {t.get('assigned_to')}")
        f = t.get("file")
        if f and not (WS / f).exists():
            problems.append(f"任务 {tid} 的任务书文件缺失: {f}")
    lock = state.get("lock") or {}
    if lock.get("holder") and lock["holder"] not in AGENTS:
        problems.append(f"锁持有者非法: {lock['holder']}")
    for a in AGENTS:
        if not (INBOX_DIR / a).is_dir():
            problems.append(f"收件箱目录缺失: inbox/{a}/")
    if ARCHIVE_FILE.exists():
        try:
            archive = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            archive = None
            problems.append(f"archive.json 解析失败: {e}")
        if archive is not None:
            if not isinstance(archive, dict):
                problems.append("archive.json 顶层必须是对象")
            else:
                archived = archive.get("archived")
                if not isinstance(archived, list):
                    problems.append("archive.json 字段 archived 必须是数组")
                else:
                    archived_ids = set()
                    state_ids = {t.get("id") for t in state.get("tasks", [])}
                    for item in archived:
                        if not isinstance(item, dict):
                            problems.append("archive.json archived 中存在非对象记录")
                            continue
                        tid = item.get("id", "(无id)")
                        if tid in archived_ids:
                            problems.append(f"归档 id 重复: {tid}")
                        archived_ids.add(tid)
                        if tid in state_ids:
                            problems.append(f"归档任务 id 与在板任务重复: {tid}")
                        if item.get("status") != "done":
                            problems.append(f"归档任务 {tid} 状态不是 done: {item.get('status')}")
                        if not item.get("archived_at"):
                            problems.append(f"归档任务 {tid} 缺少 archived_at")
                        if item.get("archived_by") not in AGENTS:
                            problems.append(f"归档任务 {tid} archived_by 非法: {item.get('archived_by')}")
                        f = item.get("file")
                        if f and not (WS / f).exists():
                            problems.append(f"归档任务 {tid} 的任务书文件缺失: {f}")
    if problems:
        for p in problems:
            print(f"[bb] ✗ {p}")
        sys.exit(1)
    ok("黑板结构完好,未发现问题")


# ---------- 入口 ----------

def main():
    p = argparse.ArgumentParser(
        prog="bb.py",
        description="共享黑板操作脚本 —— Agent 对 state.json 的唯一写入通道",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "典型流程:\n"
            "  status --agent codex          启动自举:看锁/待办/未读\n"
            "  claim task_x --agent codex    领任务(占锁,置 working)\n"
            "  done task_x --agent codex     完成(释锁,置 done)\n"
            "  set-status task_x rework --agent codex   驳回(自动计数,3 次转 blocked)\n"
            "  add-task --title ... --assign trae --agent claude   登记新任务\n"
            "  echo '正文' | send --from codex --to claude --title 'Review 结论'\n"
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="看板摘要:锁/我的待办/未读留言(启动自举第一步)")
    s.add_argument("--agent", required=True, help="我是谁: claude/codex/trae")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("claim", help="领取任务:校验指派与重试上限,占锁,置 working")
    s.add_argument("task_id")
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_claim)

    s = sub.add_parser("done", help="完成任务:置 done,释放锁")
    s.add_argument("task_id")
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_done)

    s = sub.add_parser("set-status", help="修改任务状态(rework 自动计数,达上限自动 blocked)")
    s.add_argument("task_id")
    s.add_argument("status", choices=STATUSES)
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_set_status)

    s = sub.add_parser("reassign", help="转派任务给其他 agent")
    s.add_argument("task_id")
    s.add_argument("--to", required=True)
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_reassign)

    s = sub.add_parser("add-task", help="登记新任务并生成任务书(正文可走 stdin 或 --desc)")
    s.add_argument("--id", help="缺省自动生成 task_YYYYMMDD_NN")
    s.add_argument("--title", required=True)
    s.add_argument("--assign", required=True, help="执行者: claude/codex/trae")
    s.add_argument("--type", default="feature_dev")
    s.add_argument("--desc", help="任务要求正文;不给则读 stdin,再不给则留占位符")
    s.add_argument("--agent", required=True, help="发起者(我是谁)")
    s.set_defaults(fn=cmd_add_task)

    s = sub.add_parser("send", help="定向留言(正文可走 stdin 或 --body)")
    s.add_argument("--from", dest="sender", required=True)
    s.add_argument("--to", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--body")
    s.set_defaults(fn=cmd_send)

    s = sub.add_parser("mark-read", help="标记收件箱留言为已读")
    s.add_argument("names", nargs="*", help="留言文件名(可多个)")
    s.add_argument("--all", action="store_true")
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_mark_read)

    s = sub.add_parser("unlock", help="释放锁(agent 只能释放自己的;人类干预用 --force)")
    s.add_argument("--agent")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_unlock)

    s = sub.add_parser("archive", help="归档 done 任务到 archive.json,并从在板任务移除")
    s.add_argument("task_ids", nargs="*", help="任务 id;不传则归档全部 done")
    s.add_argument("--agent", required=True)
    s.set_defaults(fn=cmd_archive)

    s = sub.add_parser("validate", help="体检:结构/状态机/文件完整性")
    s.set_defaults(fn=cmd_validate)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
