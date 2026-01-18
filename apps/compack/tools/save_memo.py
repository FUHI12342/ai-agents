from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict

from apps.compack.modules import Tool


class SaveMemoTool(Tool):
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent

    @property
    def name(self) -> str:
        return "save_memo"

    @property
    def description(self) -> str:
        return "テキストをファイルに保存します。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "保存するテキスト"},
                "filename": {"type": "string", "description": "ファイル名（省略時は自動生成）"},
            },
            "required": ["content"],
        }

    async def execute(self, content: str, filename: str | None = None) -> Dict[str, str]:
        memo_dir = self.base_dir / "logs" / "memos"
        memo_dir.mkdir(parents=True, exist_ok=True)
        safe_name = filename or f"memo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        path = memo_dir / safe_name
        path.write_text(content, encoding="utf-8")
        return {"path": str(path), "bytes": path.stat().st_size}
