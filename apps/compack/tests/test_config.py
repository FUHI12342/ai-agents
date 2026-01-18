import os
from pathlib import Path

import pytest

from apps.compack.core import ConfigManager


@pytest.mark.unit
def test_config_manager_loads_env_and_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "COMPACK_STT_OPENAI_API_KEY",
        "COMPACK_LLM_OPENAI_API_KEY",
        "COMPACK_TTS_OPENAI_API_KEY",
        "COMPACK_LLM_PROVIDER",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / "compack.env"
    env_file.write_text(
        "\n".join(
            [
                "COMPACK_STT_OPENAI_API_KEY=stt-key",
                "COMPACK_LLM_OPENAI_API_KEY=llm-key",
                "COMPACK_TTS_OPENAI_API_KEY=tts-key",
                "COMPACK_LLM_PROVIDER=ollama",
            ]
        ),
        encoding="utf-8",
    )

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
stt:
  provider: openai_whisper
  openai:
    model: whisper-1
llm:
  provider: openai_gpt4
  openai:
    model: gpt-4
    temperature: 0.6
    max_tokens: 256
  ollama:
    base_url: http://localhost:11434
    model: llama2
tts:
  provider: openai_tts
  openai:
    voice: alloy
    speed: 1.0
session:
  log_dir: "{log_dir}"
  max_context_messages: 5
audio:
  sample_rate: 8000
  channels: 1
  record_duration: 2.0
logging:
  file: "{log_file}"
  level: DEBUG
retry:
  max_attempts: 4
  base_delay: 2.0
""".format(
            log_dir=(tmp_path / "sessions").as_posix(), log_file=(tmp_path / "compack.log").as_posix()
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(env_path=env_file, config_path=config_file)
    config = manager.load()

    assert config.llm_provider == "ollama"  # env override
    assert config.stt_openai_api_key == "stt-key"
    assert config.llm_openai_api_key == "llm-key"
    assert config.tts_openai_api_key == "tts-key"
    assert config.session_log_dir == (tmp_path / "sessions")
    assert config.log_file == (tmp_path / "compack.log")
    assert config.retry_max_attempts == 4
    assert config.audio_sample_rate == 8000
    assert config.session_max_context_messages == 5
    assert manager.validate() == []


@pytest.mark.unit
def test_config_manager_validation_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "COMPACK_STT_OPENAI_API_KEY",
        "COMPACK_LLM_OPENAI_API_KEY",
        "COMPACK_TTS_OPENAI_API_KEY",
        "COMPACK_LLM_PROVIDER",
    ]:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / "empty.env"
    env_file.touch()

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
stt:
  provider: openai_whisper
llm:
  provider: openai_gpt4
tts:
  provider: openai_tts
logging:
  file: "{log_file}"
""".format(
            log_file=(tmp_path / "compack.log").as_posix()
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(env_path=env_file, config_path=config_file)
    manager.load()
    errors = manager.validate()

    assert any("OpenAI Whisper" in msg for msg in errors)
    assert any("GPT-4" in msg for msg in errors)
    assert any("TTS" in msg for msg in errors)
