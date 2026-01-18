from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Config:
    """設定データモデル."""

    # Data directories
    data_dir: Path
    session_log_dir: Path
    kb_dir: Path
    uploads_dir: Path
    config_dir: Path

    # Providers (required)
    stt_provider: str  # "openai_whisper" | "local_whisper"
    llm_provider: str  # "openai_gpt4" | "ollama"
    tts_provider: str  # "openai_tts" | "pyttsx3"

    # Privacy
    privacy_mode: str = "normal"  # strict | normal | off
    external_network: str = "ask"  # deny | allow | ask
    allow_external_categories: List[str] = None
    allow_paths: List[str] = None
    system_prompt: str = ""
    profile_name: str = "default"

    # STT
    stt_openai_api_key: Optional[str] = None
    stt_openai_model: str = "whisper-1"
    stt_local_model: str = "base"

    # LLM
    llm_openai_api_key: Optional[str] = None
    llm_openai_model: str = "gpt-4"
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_ollama_model: str = ""
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000

    # TTS
    tts_openai_api_key: Optional[str] = None
    tts_openai_voice: str = "alloy"
    tts_openai_speed: float = 1.0
    tts_pyttsx3_rate: int = 150
    tts_pyttsx3_volume: float = 1.0

    # Session
    session_max_context_messages: int = 10

    # Logging
    log_file: Optional[Path] = None
    log_level: str = "INFO"

    # Audio
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_record_duration: float = 5.0

    # Retry
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0

    def validate(self, skip_stt: bool = False, skip_tts: bool = False) -> List[str]:
        """Validate required configuration and return error messages."""
        errors: List[str] = []

        if not skip_stt and self.stt_provider == "openai_whisper" and not self.stt_openai_api_key:
            errors.append("STT: OpenAI Whisper を使用するには COMPACK_STT_OPENAI_API_KEY が必要です。")

        if self.llm_provider == "openai_gpt4" and not self.llm_openai_api_key:
            errors.append("LLM: OpenAI GPT-4 を使用するには COMPACK_LLM_OPENAI_API_KEY が必要です。")

        if not skip_tts and self.tts_provider == "openai_tts" and not self.tts_openai_api_key:
            errors.append("TTS: OpenAI TTS を使用するには COMPACK_TTS_OPENAI_API_KEY が必要です。")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Expose config as a serializable dict."""
        return {
            "data_dir": str(self.data_dir),
            "kb_dir": str(self.kb_dir),
            "uploads_dir": str(self.uploads_dir),
            "config_dir": str(self.config_dir),
            "privacy_mode": self.privacy_mode,
            "external_network": self.external_network,
            "allow_external_categories": self.allow_external_categories or [],
            "allow_paths": self.allow_paths or [],
            "system_prompt": self.system_prompt,
            "profile_name": self.profile_name,
            "stt_provider": self.stt_provider,
            "stt_openai_api_key": self.stt_openai_api_key,
            "stt_openai_model": self.stt_openai_model,
            "stt_local_model": self.stt_local_model,
            "llm_provider": self.llm_provider,
            "llm_openai_api_key": self.llm_openai_api_key,
            "llm_openai_model": self.llm_openai_model,
            "llm_ollama_base_url": self.llm_ollama_base_url,
            "llm_ollama_model": self.llm_ollama_model,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "tts_provider": self.tts_provider,
            "tts_openai_api_key": self.tts_openai_api_key,
            "tts_openai_voice": self.tts_openai_voice,
            "tts_openai_speed": self.tts_openai_speed,
            "tts_pyttsx3_rate": self.tts_pyttsx3_rate,
            "tts_pyttsx3_volume": self.tts_pyttsx3_volume,
            "session_log_dir": str(self.session_log_dir),
            "session_max_context_messages": self.session_max_context_messages,
            "log_file": str(self.log_file) if self.log_file else None,
            "log_level": self.log_level,
            "audio_sample_rate": self.audio_sample_rate,
            "audio_channels": self.audio_channels,
            "audio_record_duration": self.audio_record_duration,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_base_delay": self.retry_base_delay,
        }


@dataclass
class ToolResult:
    """ツール実行結果モデル."""

    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dict."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }
