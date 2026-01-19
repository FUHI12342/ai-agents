from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from apps.compack.core import StructuredLogger
from apps.compack.models import ToolResult


class Tool(ABC):
    """チール抽象基底クラス."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def parameters(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        raise NotImplementedError


class ToolManager:
    """チールの登録と実行を管理する。"""

    def __init__(self, logger: StructuredLogger):
        self.tools: Dict[str, Tool] = {}
        self.logger = logger

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
        self.logger.debug("ツール登録", tool=tool.name)

    def get_tool_schemas(self) -> List[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self.tools.values()
        ]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"未登録のツールです: {tool_name}")

        try:
            result = await tool.execute(**(args or {}))
            self.logger.info("ツール実行成功", tool=tool_name)
            return ToolResult(tool_name=tool_name, success=True, result=result)
        except Exception as exc:
            self.logger.error("ツール実行失敗", tool=tool_name, error=exc)
            return ToolResult(tool_name=tool_name, success=False, result=None, error=str(exc))
