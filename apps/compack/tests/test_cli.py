import pytest

from apps.compack.cli.interface import CLIInterface
from apps.compack.core import ConfigManager, SessionManager, StructuredLogger
from apps.compack.models import Config


class DummyOrchestrator:
    def __init__(self, session: SessionManager):
        self.session = session

    async def process_voice_input(self, duration=None):
        return "voice"

    async def process_text_input(self, text: str):
        return f"echo:{text}"


@pytest.mark.unit
def test_handle_command_quit(tmp_path) -> None:
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    orchestrator = DummyOrchestrator(session)
    config_manager = ConfigManager()
    cli = CLIInterface(orchestrator, config_manager)
    cli.running = True
    cli.handle_command("/quit")
    assert not cli.running


@pytest.mark.unit
def test_handle_command_config_masks_keys(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    logger = StructuredLogger(log_file=None)
    session = SessionManager(log_dir=tmp_path / "sessions", logger=logger)
    orchestrator = DummyOrchestrator(session)
    config_manager = ConfigManager()
    config_manager.config = Config(
        data_dir=tmp_path,
        session_log_dir=tmp_path / "sessions",
        kb_dir=tmp_path / "kb",
        uploads_dir=tmp_path / "uploads",
        config_dir=tmp_path / "config",
        privacy_mode="off",
        external_network="allow",
        stt_provider="openai_whisper",
        stt_openai_api_key="secret",
        stt_openai_model="whisper-1",
        stt_local_model="base",
        llm_provider="openai_gpt4",
        llm_openai_api_key="secret2",
        llm_openai_model="gpt-4",
        llm_ollama_base_url="http://localhost:11434",
        llm_ollama_model="llama2",
        llm_temperature=0.7,
        llm_max_tokens=1000,
        tts_provider="openai_tts",
        tts_openai_api_key="secret3",
        tts_openai_voice="alloy",
        tts_openai_speed=1.0,
        tts_pyttsx3_rate=150,
        tts_pyttsx3_volume=1.0,
        session_max_context_messages=5,
        log_file=None,
        log_level="INFO",
        audio_sample_rate=16000,
        audio_channels=1,
        audio_record_duration=5.0,
        retry_max_attempts=3,
        retry_base_delay=1.0,
    )
    cli = CLIInterface(orchestrator, config_manager)
    cli.handle_command("/config")
    output = capsys.readouterr().out
    assert "***" in output
