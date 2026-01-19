from __future__ import annotations

from typing import AsyncIterator, List, Optional, Tuple

import openai

from apps.compack.modules.llm import LLMProvider


class OpenAIGPT4LLM(LLMProvider):
    """OpenAI GPT-4 provider."""

    def __init__(self, api_key: str, model: str = "gpt-4", temperature: float = 0.7, max_tokens: int = 1000):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        if stream:
            for chunk in self._stream_response(messages, tools):
                yield chunk
        else:
            yield self._create_completion(messages, tools)

    def _stream_response(self, messages: List[dict], tools: Optional[List[dict]]) -> AsyncIterator[str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=True,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def _create_completion(self, messages: List[dict], tools: Optional[List[dict]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=False,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        message = response.choices[0].message
        return message.content or ""

    def should_call_tool(self, response: dict) -> Tuple[bool, Optional[dict]]:
        tool_calls = response.get("tool_calls") if isinstance(response, dict) else None
        if tool_calls:
            return True, tool_calls[0]
        return False, None
