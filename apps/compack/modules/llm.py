from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Tuple

from apps.compack.core import StructuredLogger


class LLMError(Exception):
    """LLM related errors."""


class LLMProvider(ABC):
    """LLMプロバイダ抽象基底クラス."""

    @abstractmethod
    async def generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        raise NotImplementedError

    @abstractmethod
    def should_call_tool(self, response: dict) -> Tuple[bool, Optional[dict]]:
        """Decide whether to call a tool based on the LLM response."""
        raise NotImplementedError


class LLMModule:
    """コンテキスト構築とLLM応答生成を担当."""

    def __init__(self, provider: LLMProvider, logger: StructuredLogger, max_context_messages: int = 10):
        self.provider = provider
        self.logger = logger
        self.max_context_messages = max_context_messages

    def build_context(self, history: List[dict], user_input: str) -> List[dict]:
        """Compose context using the latest N messages and current user input."""
        tail = history[-self.max_context_messages :] if self.max_context_messages else history
        context = tail + [{"role": "user", "content": user_input}]
        return context

    async def generate_response(
        self,
        context: List[dict],
        tools: Optional[List[dict]] = None,
    ) -> AsyncIterator[str]:
        """Stream responses from the provider with error handling."""
        try:
            result = self.provider.generate(context, tools=tools, stream=True)
            if hasattr(result, "__aiter__"):
                async for chunk in result:  # type: ignore[attr-defined]
                    yield chunk
            else:
                yield await result  # type: ignore[misc]
        except Exception as exc:
            self.logger.error("LLM応答生成に失敗しました", error=exc)
            raise
