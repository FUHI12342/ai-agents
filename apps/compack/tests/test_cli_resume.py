import builtins

import pytest

from apps.compack.cli.interface import CLIInterface
from apps.compack.core import ConfigManager, StructuredLogger
from apps.compack.core.session import SessionManager
from apps.compack.modules import LLMModule, LLMProvider, ToolManager
from apps.compack.core.orchestrator import ConversationOrchestrator


class EchoLLM(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        yield "ok"

    def should_call_tool(self, response):
        return False, None


def make_orchestrator(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    llm = LLMModule(EchoLLM(), logger)
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
    return orch, logger


@pytest.mark.unit
def test_init_session_invalid_id_becomes_first_message(monkeypatch, tmp_path):
    orch, _ = make_orchestrator(tmp_path)
    cfg = ConfigManager()
    cli = CLIInterface(orch, cfg)

    # create one session to trigger prompt
    sid = orch.session.create_session()
    orch.session.save_session()

    # monkeypatch input to simulate invalid session id
    monkeypatch.setattr(builtins, "input", lambda prompt="": "not-a-session-id")
    initial = cli._init_session(resume=None)
    assert initial == "not-a-session-id"
    assert orch.session.current_session_id is not None


@pytest.mark.unit
def test_resume_new_skips_prompt(monkeypatch, tmp_path):
    orch, _ = make_orchestrator(tmp_path)
    cfg = ConfigManager()
    cli = CLIInterface(orch, cfg)

    def fail_input(prompt=""):
        raise AssertionError("input should not be called when resume=new")

    monkeypatch.setattr(builtins, "input", fail_input)
    initial = cli._init_session(resume="new")
    assert initial is None
    assert orch.session.current_session_id is not None


@pytest.mark.unit
def test_external_category_skips_code_like(tmp_path):
    orch, _ = make_orchestrator(tmp_path)
    path_like = r"D:\data\scoreboard_latest.txt"
    assert orch._external_category(path_like) is None
