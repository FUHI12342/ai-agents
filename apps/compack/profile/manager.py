from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


class ProfileManager:
    """Persist lightweight user profile data (opt-in) for prompt injection."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path(__file__).parent / "profile.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8")) or {}
            except Exception:
                self.data = {}
        else:
            self.data = {}
        return self.data

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def show(self) -> Dict[str, Any]:
        return self.data

    def set_value(self, key: str, value: Any) -> Dict[str, Any]:
        self.data[key] = value
        self.save()
        return self.data

    def delete_key(self, key: str) -> Dict[str, Any]:
        if key in self.data:
            del self.data[key]
            self.save()
        return self.data

    def reset(self) -> None:
        self.data = {}
        self.save()

    def format_for_prompt(self) -> str:
        if not self.data:
            return ""
        lines = []
        for k, v in self.data.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)
