import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.modules import LLMModule, LLMProvider, ToolManager


class ToolLikeLLM(LLMProvider):
    def __init__(self):
        self.calls = 0

    async def generate(self, messages, tools=None, stream=True):
        self.calls += 1
        if self.calls == 1:
            yield '{"name": "nonexistent_tool", "arguments": {"q": "test"}}'
        else:
            yield "自然文の返答です"

    def should_call_tool(self, response):
        return False, None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tool_like_json_retried_without_showing_user(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    llm = LLMModule(ToolLikeLLM(), logger)
    orch = ConversationOrchestrator(
        stt=None,
        llm=llm,
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="allow",
    )

    response = await orch.process_text_input("テスト入力")
    assert "自然文" in response
