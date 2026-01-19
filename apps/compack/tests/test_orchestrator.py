import numpy as np
import pytest
from pathlib import Path

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.modules import (
    LLMModule,
    LLMProvider,
    STTModule,
    STTProvider,
    TTSModule,
    TTSProvider,
    Tool,
    ToolManager,
)


class StubSTTProvider(STTProvider):
    async def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        return "こんにちは"


class StubLLMProvider(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        yield "応答です"

    def should_call_tool(self, response):
        return False, None


class StubTTSProvider(TTSProvider):
    async def synthesize(self, text: str) -> bytes:
        return b"audio"


class EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "echo"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {"text": {"type": "string"}}}

    async def execute(self, **kwargs):
        return kwargs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_voice_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    logger = StructuredLogger(log_file=None)
    stt = STTModule(StubSTTProvider(), logger, sample_rate=16000, channels=1)
    monkeypatch.setattr(stt, "record_audio", lambda duration=None: (np.zeros(10, dtype=np.float32), 16000))
    llm = LLMModule(StubLLMProvider(), logger, max_context_messages=5)
    tts = TTSModule(StubTTSProvider(), logger)
    monkeypatch.setattr(tts, "play_audio", lambda audio: None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)

    orchestrator = ConversationOrchestrator(stt, llm, tts, session, tools, logger, enable_voice=True, enable_tts=True)
    response = await orchestrator.process_voice_input(duration=0.1)

    assert response == "応答です"
    assert session.messages[-1].content == "応答です"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_execute_tool(tmp_path: Path) -> None:
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    tools.register(EchoTool())
    orchestrator = ConversationOrchestrator(
        stt=STTModule(StubSTTProvider(), logger, sample_rate=16000, channels=1),
        llm=LLMModule(StubLLMProvider(), logger),
        tts=TTSModule(StubTTSProvider(), logger),
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
    )
    result = await orchestrator.execute_tool("echo", {"text": "ping"})
    assert result["success"]
    assert session.messages[-1].metadata["tool"] == "echo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_text_mode_no_tts(tmp_path: Path) -> None:
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orchestrator = ConversationOrchestrator(
        stt=None,
        llm=LLMModule(StubLLMProvider(), logger),
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
    )
    response = await orchestrator.process_text_input("text only")
    assert response == "応答です"
