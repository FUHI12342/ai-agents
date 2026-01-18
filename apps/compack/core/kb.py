from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"\w+", text)]


class KBManager:
    """シンプルなローカルKB管理（トークン重複による類似度計算）。"""

    def __init__(self, kb_dir: Path):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.kb_dir / "kb_index.jsonl"

    def _load_index(self) -> List[Dict]:
        if not self.index_path.exists():
            return []
        lines = self.index_path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _save_index(self, entries: List[Dict]) -> None:
        self.index_path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries), encoding="utf-8")

    def add_path(self, path: Path) -> int:
        path = Path(path)
        entries = self._load_index()
        if path.is_dir():
            files = list(path.rglob("*"))
        else:
            files = [path]
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
        self._save_index(entries)
        return added

    def status(self) -> Dict[str, int]:
        entries = self._load_index()
        return {"entries": len(entries)}

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        entries = self._load_index()
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
                raise RuntimeError("PyPDF2 がインストールされていません。")
            text = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        return path.read_text(encoding="utf-8", errors="ignore")
