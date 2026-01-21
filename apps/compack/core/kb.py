from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"\w+", text)]


class KBManager:
    """Simple filesystem-based KB manager with persona-aware directories."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)

    def _persona_dir(self, persona: Optional[str]) -> Path:
        return self.kb_dir / (persona or "default")

    def _index_path(self, persona: Optional[str]) -> Path:
        return self._persona_dir(persona) / "kb_index.jsonl"

    def _load_index(self, persona: Optional[str]) -> List[Dict]:
        index_path = self._index_path(persona)
        if not index_path.exists():
            return []
        lines = index_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _save_index(self, entries: List[Dict], persona: Optional[str]) -> None:
        index_path = self._index_path(persona)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries), encoding="utf-8")

    def add_path(self, path: Path, persona: Optional[str] = None) -> int:
        path = Path(path)
        entries = self._load_index(persona)
        files = list(path.rglob("*")) if path.is_dir() else [path]
        added = 0
        for f in files:
            if f.is_dir():
                continue
            if f.suffix.lower() not in {".txt", ".md", ".json", ".pdf"}:
                continue
            try:
                content = self._read_file(f)
            except Exception:
                continue
            tokens = _tokenize(content)
            entries.append({"path": str(f.resolve()), "tokens": tokens, "preview": content[:200]})
            added += 1
        self._save_index(entries, persona)
        return added

    def status(self) -> Dict[str, Dict[str, int]]:
        persona_status: Dict[str, Dict[str, int]] = {}
        for idx in self.kb_dir.glob("*/kb_index.jsonl"):
            persona = idx.parent.name
            entries = self._load_index(persona)
            persona_status[persona] = {"entries": len(entries)}
        if "default" not in persona_status:
            persona_status["default"] = {"entries": len(self._load_index("default"))}
        total = sum(v.get("entries", 0) for v in persona_status.values())
        return {"total_entries": total, "by_persona": persona_status}

    def search(self, query: str, top_k: int = 3, persona: Optional[str] = None) -> List[Dict]:
        entries = self._load_index(persona)
        if persona and not entries:
            entries = self._load_index("default")
        q_tokens = set(_tokenize(query))
        scored: List[Tuple[float, Dict]] = []
        for e in entries:
            tokens = set(e.get("tokens", []))
            if not tokens:
                continue
            score = len(q_tokens & tokens) / max(1, len(q_tokens | tokens))
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(match=e[1], score=float(e[0])) for e in scored[:top_k]]

    def _read_file(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            try:
                import PyPDF2  # type: ignore
            except ImportError:
                raise RuntimeError("PyPDF2 is required to read PDF files for KB ingestion.")
            text = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        return path.read_text(encoding="utf-8", errors="ignore")
