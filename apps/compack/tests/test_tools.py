from pathlib import Path
from typing import Any, Dict

import pytest
from hypothesis import given, strategies as st

from apps.compack.core import StructuredLogger
from apps.compack.modules import Tool, ToolManager
from apps.compack.tools import SaveMemoTool, SearchFilesTool, SetTimerTool


class DummyTool(Tool):
    def __init__(self, name: str = "dummy"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "dummy"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        return {"echo": kwargs}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_memo_tool(tmp_path: Path) -> None:
    manager = ToolManager(logger=StructuredLogger(log_file=None))
    memo_tool = SaveMemoTool(base_dir=tmp_path)
    manager.register(memo_tool)

    result = await manager.execute("save_memo", {"content": "hello", "filename": "test.txt"})
    data = result.to_dict()
    assert data["success"]
    assert "path" in data["result"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_files_tool(tmp_path: Path) -> None:
    target = tmp_path / "notes"
    target.mkdir()
    file_path = target / "match_query.txt"
    file_path.write_text("content", encoding="utf-8")

    manager = ToolManager(logger=StructuredLogger(log_file=None))
    manager.register(SearchFilesTool())
    result = await manager.execute("search_files", {"query": "match", "directory": str(tmp_path)})
    data = result.to_dict()
    assert data["success"]
    assert str(file_path) in data["result"]["results"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_timer_tool() -> None:
    manager = ToolManager(logger=StructuredLogger(log_file=None))
    manager.register(SetTimerTool())
    result = await manager.execute("set_timer", {"seconds": 0, "message": "done"})
    assert result.success
    assert result.result["message"] == "done"


@pytest.mark.property
@pytest.mark.asyncio
@given(tool_name=st.text(min_size=3, max_size=10))
async def test_tool_registration_dynamic(tool_name: str) -> None:
    """
    Feature: voice-ai-agent-compack, Property 11: チール動的登録の拡張性.
    """
    manager = ToolManager(logger=StructuredLogger(log_file=None))
    manager.register(DummyTool(name=tool_name))
    schemas = manager.get_tool_schemas()
    assert any(schema["name"] == tool_name for schema in schemas)
    result = await manager.execute(tool_name, {"value": 1})
    assert result.success


@pytest.mark.property
@pytest.mark.asyncio
@given(payload=st.dictionaries(keys=st.text(min_size=1, max_size=5), values=st.integers()))
async def test_tool_execution_returns_result(payload: Dict[str, Any]) -> None:
    """
    Feature: voice-ai-agent-compack, Property 10: チール実行と結果処理.
    """
    manager = ToolManager(logger=StructuredLogger(log_file=None))
    manager.register(DummyTool())
    result = await manager.execute("dummy", payload)
    assert result.success
    assert result.result["echo"] == payload
