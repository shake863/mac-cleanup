from __future__ import annotations
import glob as _glob
import json as _json
from dataclasses import asdict, dataclass
from pathlib import Path
from ..config import decided_paths
from ..paths import expand, human
from ..rules import load_rules
from ..safety import safety_hit

@dataclass
class Candidate:
    path: str
    category: str            # cache|dev|leftover|bigfile|system
    size: int
    evidence: str
    risk: str                # recommend | caution
    suggested_strategy: str  # empty-dir | delete

def rule_covered(rules_path=None) -> set[str]:
    covered: set[str] = set()
    prules, _crules, _ = load_rules(rules_path)
    for r in prules:
        for raw in r.paths:
            s = str(expand(raw))
            if any(ch in s for ch in "*?["):
                covered.update(_glob.glob(s))
            else:
                covered.add(s)
    return covered

def _admit(cands: list[Candidate], seen: set[str]) -> list[Candidate]:
    out = []
    for c in cands:
        if c.path in seen or safety_hit(Path(c.path)):
            continue
        seen.add(c.path)
        out.append(c)
    return out

def run_scan(categories=None, threshold_mb: int = 500, dirs=None,
             rules_path=None) -> list[Candidate]:
    from . import bigfile, cache, dev, leftover, systemitems
    cats = categories if categories is not None else \
        ["cache", "dev", "leftover", "bigfile", "system"]
    seen = set(decided_paths()) | rule_covered(rules_path)
    out: list[Candidate] = []
    if "cache" in cats:
        out += _admit(cache.scan(), seen)
    if "dev" in cats:
        out += _admit(dev.scan(), seen)
    if "leftover" in cats:
        out += _admit(leftover.scan(), seen)
    if "bigfile" in cats:
        out += _admit(bigfile.scan(threshold_mb, dirs), seen)
    if "system" in cats:
        out += _admit(systemitems.scan(), seen)
    out.sort(key=lambda c: c.size, reverse=True)
    return out

def render_json(cands: list[Candidate]) -> str:
    return _json.dumps([asdict(c) for c in cands], ensure_ascii=False, indent=2)

def render_table(cands: list[Candidate]) -> str:
    lines = [f"{'体积':>10}  {'类别':<8} {'风险':<9} 路径"]
    for c in cands:
        lines.append(f"{human(c.size):>10}  {c.category:<8} {c.risk:<9} {c.path}")
        if c.evidence:
            lines.append(f"{'':>10}  {'':<8} {'':<9} └ {c.evidence}")
    return "\n".join(lines)
