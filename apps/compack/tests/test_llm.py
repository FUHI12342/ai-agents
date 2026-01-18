import asyncio
from typing import AsyncIterator, List, Optional, Tuple

import pytest
from hypothesis import given, strategies as st

from apps.compack.core import StructuredLogger
from apps.compack.modules import LLMModule, LLMProvider


class FakeLLMProvider(LLMProvider):
    def __init__(self, chunks: List[str]):
        self.chunks = chunks

    async def generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        for chunk in self.chunks:
            yield chunk

    def should_call_tool(self, response: dict) -> Tuple[bool, Optional[dict]]:
        return False, None


class FailingLLMProvider(LLMProvider):
    async def generate(self, messages: List[dict], tools: Optional[List[dict]] = None, stream: bool = True):
        raise RuntimeError("missing api key")

    def should_call_tool(self, response: dict) -> Tuple[bool, Optional[dict]]:
        return False, None


@pytest.mark.unit
def test_build_context_trims_history() -> None:
    history = [{"role": "user", "content": f"msg-{i}"} for i in range(20)]
    logger = StructuredLogger(log_file=None)
    module = LLMModule(FakeLLMProvider([]), logger, max_context_messages=5)

    context = module.build_context(history, "latest")
    assert len(context) == 6  # 5 history + user message
    assert context[-1]["content"] == "latest"
    assert context[0]["content"] == "msg-15"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_streams_chunks() -> None:
    provider = FakeLLMProvider(["hello", " ", "world"])
    logger = StructuredLogger(log_file=None)
    module = LLMModule(provider, logger, max_context_messages=3)

    collected = []
    async for chunk in module.generate_response([{"role": "user", "content": "hi"}]):
        collected.append(chunk)

    assert "".join(collected) == "hello world"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_response_propagates_errors() -> None:
    module = LLMModule(FailingLLMProvider(), StructuredLogger(log_file=None))
    with pytest.raises(RuntimeError):
        async for _ in module.generate_response([{"role": "user", "content": "hi"}]):
            pass


@pytest.mark.property
@given(
    history=st.lists(
        st.fixed_dictionaries({"role": st.sampled_from(["user", "assistant"]), "content": st.text(min_size=1, max_size=20)}),
        min_size=1,
        max_size=15,
    ),
    user_input=st.text(min_size=1, max_size=20),
)
def test_context_includes_latest_messages(history: List[dict], user_input: str) -> None:
    """
    Feature: voice-ai-agent-compack, Property 3: LLMコンテキスト構築の完備性.
    """
    module = LLMModule(FakeLLMProvider([]), StructuredLogger(log_file=None), max_context_messages=10)
    context = module.build_context(history, user_input)

    assert context[-1]["content"] == user_input
    assert len(context) <= 11
    assert context[:-1] == history[-10:]


@pytest.mark.property
@pytest.mark.asyncio
@given(chunks=st.lists(st.text(min_size=0, max_size=10), min_size=1, max_size=5))
async def test_streaming_concat_preserves_order(chunks: List[str]) -> None:
    """
    Feature: voice-ai-agent-compack, Property 4: ストリーミング応答の逐次性.
    """
    provider = FakeLLMProvider(chunks)
    module = LLMModule(provider, StructuredLogger(log_file=None))
    result_parts: List[str] = []
    async for chunk in module.generate_response([{"role": "user", "content": "hi"}]):
        result_parts.append(chunk)
    assert "".join(chunks) == "".join(result_parts)
