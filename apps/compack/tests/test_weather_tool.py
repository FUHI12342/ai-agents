import pytest

from apps.compack.core import ConversationOrchestrator, SessionManager, StructuredLogger
from apps.compack.models import ToolResult
from apps.compack.modules import LLMModule, LLMProvider, ToolManager
from apps.compack.tools.weather import WeatherTool


class StubLLM(LLMProvider):
    async def generate(self, messages, tools=None, stream=True):
        yield "ok"

    def should_call_tool(self, response):
        return False, None


@pytest.mark.asyncio
async def test_weather_tool_parses(monkeypatch):
    sample = {
        "current_condition": [{"temp_C": "20", "FeelsLikeC": "19", "weatherDesc": [{"value": "Sunny"}]}],
        "weather": [
            {"date": "2026-01-16", "maxtempC": "22", "mintempC": "12", "hourly": [{"chanceofrain": "10"}]},
            {"date": "2026-01-17", "maxtempC": "24", "mintempC": "14", "hourly": [{"chanceofrain": "20"}]},
        ],
    }

    class Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return sample

    monkeypatch.setattr("apps.compack.tools.weather.requests.get", lambda *a, **k: Resp())
    tool = WeatherTool()
    summary = await tool.execute(location="Tokyo")
    assert "summary" in summary
    assert summary["today"]["maxtempC"] == "22"


@pytest.mark.asyncio
async def test_external_flow_weather_yes(monkeypatch, tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tool_result = ToolResult(tool_name="weather", success=True, result={"summary": "sunny"}, error=None)
    tools = ToolManager(logger=logger)

    async def fake_execute(name, args):
        fake_execute.called = True
        fake_execute.args = (name, args)
        return tool_result

    fake_execute.called = False
    fake_execute.args = None
    monkeypatch.setattr(tools, "execute", fake_execute)

    orch = ConversationOrchestrator(
        stt=None,
        llm=LLMModule(StubLLM(), logger),
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="ask",
    )

    msg1 = await orch.process_text_input("明日の天気は？")
    assert "外部アクセス" in msg1
    msg2 = await orch.process_text_input("yes")
    assert "地域名" in msg2
    msg3 = await orch.process_text_input("Tokyo")
    assert "sunny" in msg3
    assert fake_execute.called
    assert fake_execute.args[1]["location"] == "Tokyo"


@pytest.mark.asyncio
async def test_external_flow_weather_deny(tmp_path):
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    tools = ToolManager(logger=logger)
    orch = ConversationOrchestrator(
        stt=None,
        llm=LLMModule(StubLLM(), logger),
        tts=None,
        session=session,
        tools=tools,
        logger=logger,
        enable_voice=False,
        enable_tts=False,
        external_mode="deny",
    )
    msg = await orch.process_text_input("天気を教えて")
    assert "外部アクセスは無効" in msg
