import json
import numpy as np
import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.modules import LLMModule, LLMProvider, STTModule, STTProvider, TTSModule, TTSProvider, ToolManager


class IntegrationSTT(STTProvider):
    async def transcribe(self, audio_data, sample_rate):
        return "テキスト入力"


class IntegrationLLM(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        yield "統合テスト応答"

    def should_call_tool(self, response):
        return False, None


class IntegrationTTS(TTSProvider):
    async def synthesize(self, text: str) -> bytes:
        return b"audio-bytes"


@pytest.mark.asyncio
async def test_end_to_end_flow(tmp_path) -> None:
    logger = StructuredLogger(log_file=None)
    stt = STTModule(IntegrationSTT(), logger, sample_rate=16000, channels=1)
    llm = LLMModule(IntegrationLLM(), logger)
    tts = TTSModule(IntegrationTTS(), logger)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orchestrator = ConversationOrchestrator(stt, llm, tts, session, tools, logger)

    response = await orchestrator.process_text_input("こんにちは")
    assert response == "統合テスト応答"

    saved_files = list((tmp_path / "sessions").glob("*.jsonl"))
    assert saved_files
    content = saved_files[0].read_text(encoding="utf-8").splitlines()
    assert len(content) >= 2
    for line in content:
        assert json.loads(line)
