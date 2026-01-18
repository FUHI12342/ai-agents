import pytest
from unittest import mock

import apps.compack.main as main
from apps.compack.core import ConfigManager, StructuredLogger
from apps.compack.main import build_llm, build_stt, build_tts
from apps.compack.models import Config
from apps.compack.providers.llm import OllamaLLM, OpenAIGPT4LLM
from apps.compack.providers.stt import LocalWhisperSTT, OpenAIWhisperSTT
from apps.compack.providers.tts import OpenAITTSTTS, Pyttsx3TTS


def make_config(tmp_path, stt_provider: str, llm_provider: str, tts_provider: str) -> Config:
    return Config(
        data_dir=tmp_path,
        session_log_dir=tmp_path / "sessions",
        kb_dir=tmp_path / "kb",
        uploads_dir=tmp_path / "uploads",
        config_dir=tmp_path / "config",
            privacy_mode="off",
        external_network="allow",
        stt_provider=stt_provider,
        stt_openai_api_key="stt-key",
        stt_openai_model="whisper-1",
        stt_local_model="base",
        llm_provider=llm_provider,
        llm_openai_api_key="llm-key",
        llm_openai_model="gpt-4",
        llm_ollama_base_url="http://localhost:11434",
        llm_ollama_model="llama2",
        llm_temperature=0.7,
        llm_max_tokens=256,
        tts_provider=tts_provider,
        tts_openai_api_key="tts-key",
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


@pytest.mark.property
def test_provider_switching(tmp_path) -> None:
    """
    Feature: voice-ai-agent-compack, Property 12: プロバイダ切り替えの一貫性.
    """
    cfg_manager = ConfigManager()
    logger = StructuredLogger(log_file=None)

    cfg_manager.config = make_config(tmp_path, "openai_whisper", "openai_gpt4", "openai_tts")
    stt_module = build_stt(cfg_manager.config, logger)
    llm_module = build_llm(cfg_manager.config, logger)
    tts_module = build_tts(cfg_manager.config, logger)

    assert isinstance(stt_module.provider, OpenAIWhisperSTT)
    assert isinstance(llm_module.provider, OpenAIGPT4LLM)
    assert isinstance(tts_module.provider, OpenAITTSTTS)

    cfg_manager.config = make_config(tmp_path, "local_whisper", "ollama", "pyttsx3")
    with mock.patch.object(main, "LocalWhisperSTT") as mock_local:
        mock_local.return_value = object()
        stt_module_local = build_stt(cfg_manager.config, logger)
        assert stt_module_local.provider is mock_local.return_value

    with mock.patch.object(main, "OllamaLLM") as mock_ollama:
        ollama_instance = mock.Mock()
        ollama_instance.model = "llama2"
        ollama_instance.ensure_model_exists.return_value = {"auto_selected": False, "model_exists": True}
        mock_ollama.return_value = ollama_instance
        llm_module_local = build_llm(cfg_manager.config, logger)

    # pyttsx3 is optional; skip if unavailable.
    try:
        import pyttsx3  # noqa: F401
    except ImportError:
        pytest.skip("pyttsx3 not installed")
    tts_module_local = build_tts(cfg_manager.config, logger)
    assert llm_module_local.provider is ollama_instance
    assert isinstance(tts_module_local.provider, Pyttsx3TTS)
