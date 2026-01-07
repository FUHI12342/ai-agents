# trader/housekeeping.py
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class Rule:
    glob: str
    keep_days: int
    protect_substrings: Tuple[str, ...] = ("latest", "history", ".gitkeep")


DEFAULT_RULES: List[Rule] = [
    Rule("scripts/logs/daily_run_*.log", keep_days=30),
    Rule("reports/daily_body_*.txt", keep_days=30),
    Rule("reports/*.json", keep_days=30),
    Rule("trader/reports/reconcile_*.txt", keep_days=30),
    Rule("trader/reports/reconcile_*.json", keep_days=30),
    Rule("trader/reports/go_nogo_*.txt", keep_days=30),
    Rule("trader/reports/alert_sent_*.flag", keep_days=7),
]


def _is_protected(path: Path, protect_substrings: Tuple[str, ...]) -> bool:
    name = path.name.lower()
    return any(s.lower() in name for s in protect_substrings)


def _iter_matches(root: Path, rule: Rule) -> Iterable[Path]:
    yield from root.glob(rule.glob)


def collect_deletes(root: Path, rules: List[Rule], now: datetime) -> List[Path]:
    deletes: List[Path] = []
    for rule in rules:
        cutoff = now - timedelta(days=rule.keep_days)
        for p in _iter_matches(root, rule):
            if not p.exists() or not p.is_file():
                continue

            # 絶対触らない
            parts = {x.lower() for x in p.parts}
            if ".git" in parts or ".venv" in parts:
                continue

            if _is_protected(p, rule.protect_substrings):
                continue

            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime < cutoff:
                deletes.append(p)

    uniq = sorted(set(deletes), key=lambda x: str(x))
    return uniq


def apply_deletes(paths: List[Path], dry_run: bool) -> int:
    count = 0
    for p in paths:
        if dry_run:
            print(f"[DRYRUN] delete: {p}")
            continue
        try:
            p.unlink(missing_ok=True)
            print(f"[OK] deleted: {p}")
            count += 1
        except Exception as e:
            print(f"[WARN] failed delete: {p} ({e})")
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root (ai-agents)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-days-logs", type=int, default=30)
    ap.add_argument("--keep-days-reports", type=int, default=30)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERROR] root not found: {root}")
        return 2

    # 安全弁
    if "ai-agents" not in str(root).lower():
        print(f"[ERROR] root does not look like ai-agents repo: {root}")
        return 2

    # keep日数をざっくり反映
    rules: List[Rule] = []
    for r in DEFAULT_RULES:
        keep = r.keep_days
        if r.glob.startswith("scripts/logs/"):
            keep = args.keep_days_logs
        if r.glob.startswith("reports/") or r.glob.startswith("trader/reports/"):
            keep = args.keep_days_reports
        rules.append(Rule(r.glob, keep, r.protect_substrings))

    now = datetime.now()
    deletes = collect_deletes(root, rules, now)
    print(f"[INFO] candidates={len(deletes)}")
    for p in deletes[:20]:
        print(f"[INFO] candidate: {p}")
    if len(deletes) > 20:
        print(f"[INFO] ... and {len(deletes)-20} more")

    deleted = apply_deletes(deletes, dry_run=args.dry_run)
    print(f"[INFO] deleted={deleted} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())