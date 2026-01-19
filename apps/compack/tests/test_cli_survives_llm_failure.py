import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.modules import (
    LLMModule,
    LLMProvider,
    STTModule,
    STTProvider,
    ToolManager,
)


class FailingLLMProvider(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        raise RuntimeError("boom")

    def should_call_tool(self, response):
        return False, None


class NoopSTT(STTProvider):
    async def transcribe(self, audio_data, sample_rate: int) -> str:
        return "noop"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cli_survives_llm_failure(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    stt = STTModule(NoopSTT(), logger, sample_rate=16000, channels=1)
    llm = LLMModule(FailingLLMProvider(), logger)

    orchestrator = ConversationOrchestrator(
        stt=stt,
        llm=llm,
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
    )

    response = await orchestrator.process_text_input("hello")
    assert "LLM" in response
    assert "diagnose" in response
