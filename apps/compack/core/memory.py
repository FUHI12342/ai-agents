from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class MemoryEntry:
    role: str
    content: str
    ts: str
    metadata: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {"role": self.role, "content": self.content, "ts": self.ts, "metadata": self.metadata},
            ensure_ascii=False,
        )


class MemoryManager:
    """Lightweight JSONL-backed memory store."""

    def __init__(self, path: Path, mode: str = "manual"):
        self.path = path
        self.mode = mode
        self.entries: List[MemoryEntry] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                self.entries.append(
                    MemoryEntry(
                        role=data.get("role", ""),
                        content=data.get("content", ""),
                        ts=data.get("ts", ""),
                        metadata=data.get("metadata", {}) or {},
                    )
                )
        except Exception:
            # Corrupted memory is non-fatal; start fresh
            self.entries = []

    def add(self, role: str, content: str, metadata: Dict[str, Any] | None = None) -> None:
        entry = MemoryEntry(
            role=role,
            content=content,
            ts=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )
        self.entries.append(entry)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

    def summarize(self, exclude_latest: int = 0, limit: int = 5) -> str:
        items = self.entries
        if exclude_latest > 0:
            items = items[: -exclude_latest] if len(items) > exclude_latest else []
        if not items:
            return ""
        tail = items[-limit:]
        lines = []
        for e in tail:
            trimmed = e.content.replace("\n", " ").strip()
            if len(trimmed) > 200:
                trimmed = trimmed[:200] + "..."
            lines.append(f"- {e.role}: {trimmed}")
        return "\n".join(lines)

    def show(self, limit: int = 10) -> List[Dict[str, Any]]:
        subset = self.entries[-limit:]
        return [
            {"role": e.role, "content": e.content, "ts": e.ts, "metadata": e.metadata}
            for e in subset
        ]

    def status(self) -> Dict[str, Any]:
        last_ts = self.entries[-1].ts if self.entries else None
        return {"count": len(self.entries), "last_ts": last_ts, "mode": self.mode}
