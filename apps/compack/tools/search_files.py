from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from apps.compack.modules import Tool


class SearchFilesTool(Tool):
    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return "ローカルファイルを検索します。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索クエリ"},
                "directory": {"type": "string", "description": "検索ディレクトリ（省略時はカレント）"},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, directory: str = ".") -> Dict[str, List[str]]:
        root = Path(directory).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"検索ディレクトリが存在しません: {root}")

        matches = []
        for path in root.rglob("*"):
            if path.is_file() and query.lower() in path.name.lower():
                matches.append(str(path))
            if len(matches) >= 50:
                break
        return {"query": query, "results": matches}
