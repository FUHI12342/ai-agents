import asyncio
from pathlib import Path

import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.core.kb import KBManager
from apps.compack.modules import LLMModule, LLMProvider, ToolManager


class StubLLMProvider(LLMProvider):
    def __init__(self):
        self.last_context = None

    async def generate(self, messages, tools=None, stream=True):
        self.last_context = messages
        yield "ok"

    def should_call_tool(self, response):
        return False, None


@pytest.mark.asyncio
async def test_retrieved_context_injected(tmp_path: Path):
    kb_dir = tmp_path / "kb"
    kb = KBManager(kb_dir)
    doc = tmp_path / "doc.txt"
    doc.write_text("alpha beta gamma", encoding="utf-8")
    kb.add_path(doc, persona="default")

    logger = StructuredLogger(log_file=None)
    provider = StubLLMProvider()
    llm = LLMModule(provider, logger, max_context_messages=5)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger, max_context_messages=5)
    tools = ToolManager(logger=logger)

    orch = ConversationOrchestrator(
        stt=None,
        llm=llm,
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        external_mode="allow",
        kb=kb,
        rag_enabled=True,
        rag_top_k=3,
        persona_prompt="Persona block",
    )

    await orch.process_text_input("alpha question")
    system_msg = provider.last_context[0]["content"]
    assert "Retrieved Context" in system_msg
    assert "alpha beta gamma" in system_msg
    assert system_msg.strip().endswith("Persona block")


@pytest.mark.asyncio
async def test_persona_specific_kb_used(tmp_path: Path):
    kb_dir = tmp_path / "kb"
    kb = KBManager(kb_dir)
    default_doc = tmp_path / "default.txt"
    default_doc.write_text("default info", encoding="utf-8")
    kb.add_path(default_doc, persona="default")
    dev_doc = tmp_path / "dev.txt"
    dev_doc.write_text("dev only info", encoding="utf-8")
    kb.add_path(dev_doc, persona="dev")

    logger = StructuredLogger(log_file=None)
    provider = StubLLMProvider()
    llm = LLMModule(provider, logger, max_context_messages=5)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger, max_context_messages=5)
    tools = ToolManager(logger=logger)

    orch = ConversationOrchestrator(
        stt=None,
        llm=llm,
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        external_mode="allow",
        kb=kb,
        rag_enabled=True,
        rag_top_k=1,
        persona_name="dev",
        persona_prompt="Persona block",
    )

    await orch.process_text_input("info request")
    system_msg = provider.last_context[0]["content"]
    assert "dev only info" in system_msg
    assert "default info" not in system_msg
