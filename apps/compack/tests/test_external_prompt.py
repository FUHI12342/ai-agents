import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.modules import LLMModule, LLMProvider, ToolManager


class EchoLLM(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        last_user = ""
        for m in messages:
            if m.get("role") == "user":
                last_user = m.get("content", "")
        yield last_user

    def should_call_tool(self, response):
        return False, None


@pytest.mark.unit
def test_external_category_detects_weather_and_general(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path, logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(None, LLMModule(EchoLLM(), logger), None, session, tools, logger, enable_voice=False, enable_tts=False)
    assert orch._external_category("明日の天気を教えて") == "weather"
    assert orch._external_category("latest news please") == "general"
    assert orch._external_category("hello") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_external_ask_prompts_confirmation(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(
        None,
        LLMModule(EchoLLM(), logger),
        None,
        session,
        tools,
        logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="ask",
    )
    msg = await orch.process_text_input("明日の天気は？")
    assert "外部アクセス" in msg
    msg2 = await orch.process_text_input("no")
    assert "外部アクセスなし" in msg2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_external_deny_returns_guidance(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(
        None,
        LLMModule(EchoLLM(), logger),
        None,
        session,
        tools,
        logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="deny",
    )
    msg = await orch.process_text_input("最新ニュースを教えて")
    assert "外部アクセスは無効" in msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_external_ask_yes_allows_llm_for_general(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(
        None,
        LLMModule(EchoLLM(), logger),
        None,
        session,
        tools,
        logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="ask",
    )
    await orch.process_text_input("latest news?")
    msg = await orch.process_text_input("yes")
    assert msg == "latest news?"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_external_category_disallowed_by_allowlist(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(
        None,
        LLMModule(EchoLLM(), logger),
        None,
        session,
        tools,
        logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="ask",
        allow_external_categories=["weather"],
    )
    msg = await orch.process_text_input("latest news?")
    assert "許可されていません" in msg
