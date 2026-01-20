from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional

import yaml
from dotenv import load_dotenv

from apps.compack.models import Config


ALLOWED_STT = {"openai_whisper", "local_whisper"}
ALLOWED_LLM = {"openai_gpt4", "ollama"}
ALLOWED_TTS = {"openai_tts", "pyttsx3"}


class ConfigManager:
    """Load Compack configuration from env + YAML with sane defaults."""

    def __init__(self, env_path: Optional[Path] = None, config_path: Optional[Path] = None):
        self.env_path = Path(env_path) if env_path else Path(".env")
        self.config_path = Path(config_path) if config_path else Path("apps/compack/config.yaml")
        self.base_dir = Path(__file__).resolve().parent.parent
        self.config: Optional[Config] = None

    def load(self) -> Config:
        """Load .env and YAML config into a Config dataclass."""
        load_dotenv(self.env_path, override=False)
        yaml_config = self._load_yaml(self.config_path)
        self.config = self._compose_config(yaml_config)
        return self.config

    def reload(self) -> Config:
        """Reload configuration to reflect runtime changes."""
        return self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """Get an arbitrary config attribute."""
        if self.config is None:
            self.load()
        return getattr(self.config, key, default)

    def get_stt_provider(self) -> str:
        if self.config is None:
            self.load()
        return self.config.stt_provider

    def get_llm_provider(self) -> str:
        if self.config is None:
            self.load()
        return self.config.llm_provider

    def get_tts_provider(self) -> str:
        if self.config is None:
            self.load()
        return self.config.tts_provider

    def validate(self, mode: str = "voice") -> List[str]:
        """Validate current configuration and return error messages."""
        if self.config is None:
            self.load()
        errors: List[str] = []
        cfg = self.config

        if cfg.stt_provider not in ALLOWED_STT:
            errors.append(f"Invalid STT provider: {cfg.stt_provider} (allowed: {', '.join(ALLOWED_STT)})")
        if cfg.tts_provider not in ALLOWED_TTS:
            errors.append(f"Invalid TTS provider: {cfg.tts_provider} (allowed: {', '.join(ALLOWED_TTS)})")
        if cfg.llm_provider not in ALLOWED_LLM:
            errors.append(f"Invalid LLM provider: {cfg.llm_provider} (allowed: {', '.join(ALLOWED_LLM)})")

        if mode != "text":
            errors.extend(cfg.validate(skip_stt=False, skip_tts=False))
        else:
            errors.extend(cfg.validate(skip_stt=True, skip_tts=True))
        return errors

    def _load_yaml(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _resolve_path(self, value: Optional[str]) -> Optional[Path]:
        if value is None:
            return None
        value_path = Path(value)
        if value_path.is_absolute():
            return value_path
        return (self.base_dir / value_path).resolve()

    def _default_data_dir(self) -> Path:
        env_dir = os.getenv("COMPACK_DATA_DIR")
        if env_dir:
            return Path(env_dir).expanduser()
        if os.name == "nt":
            base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
            return Path(base) / "Compack"
        return Path.home() / ".compack"

    def _get_list_env(self, var: str) -> Optional[List[str]]:
        val = os.getenv(var)
        if not val:
            return None
        return [v.strip() for v in val.split(",") if v.strip()]

    def _compose_config(self, raw: dict) -> Config:
        stt_cfg = raw.get("stt", {})
        llm_cfg = raw.get("llm", {})
        tts_cfg = raw.get("tts", {})
        session_cfg = raw.get("session", {})
        audio_cfg = raw.get("audio", {})
        logging_cfg = raw.get("logging", {})
        retry_cfg = raw.get("retry", {})
        privacy_cfg = raw.get("privacy", {})
        data_cfg = raw.get("data", {})
        memory_cfg = raw.get("memory", {})
        profile_cfg = raw.get("profile", {})

        stt_provider = os.getenv("COMPACK_STT_PROVIDER", stt_cfg.get("provider", "local_whisper"))
        llm_provider = os.getenv("COMPACK_LLM_PROVIDER", llm_cfg.get("provider", "ollama"))
        tts_provider = os.getenv("COMPACK_TTS_PROVIDER", tts_cfg.get("provider", "pyttsx3"))

        log_level = os.getenv("COMPACK_LOG_LEVEL", logging_cfg.get("level", "INFO"))
        log_file = self._resolve_path(logging_cfg.get("file", "logs/compack.log"))

        base_data_dir = self._resolve_path(data_cfg.get("dir")) or self._default_data_dir()
        session_log_dir = self._resolve_path(session_cfg.get("log_dir")) or (base_data_dir / "sessions")
        kb_dir = base_data_dir / "kb"
        uploads_dir = base_data_dir / "uploads"
        config_dir = base_data_dir / "config"

        privacy_mode = str(os.getenv("COMPACK_PRIVACY_MODE", privacy_cfg.get("mode", "normal"))).lower()
        external_network = str(os.getenv("COMPACK_EXTERNAL_NETWORK", privacy_cfg.get("external", "ask"))).lower()
        allow_external_categories = self._get_list_env("COMPACK_ALLOW_EXTERNAL_CATEGORIES") or privacy_cfg.get(
            "allow_external_categories", []
        )
        allow_paths = self._get_list_env("COMPACK_ALLOW_PATHS") or privacy_cfg.get("allow_paths", [])
        system_prompt = str(
            os.getenv(
                "COMPACK_SYSTEM_PROMPT",
                profile_cfg.get("system_prompt", privacy_cfg.get("system_prompt", raw.get("system_prompt", ""))),
            )
        )
        profile_name = str(os.getenv("COMPACK_PROFILE", profile_cfg.get("name", raw.get("profile_name", "default"))))
        memory_mode = str(os.getenv("COMPACK_MEMORY_MODE", memory_cfg.get("mode", "manual"))).lower()

        config = Config(
            data_dir=base_data_dir,
            session_log_dir=session_log_dir,
            kb_dir=kb_dir,
            uploads_dir=uploads_dir,
            config_dir=config_dir,
            privacy_mode=privacy_mode,
            external_network=external_network,
            allow_external_categories=allow_external_categories,
            allow_paths=allow_paths,
            system_prompt=system_prompt,
            profile_name=profile_name,
            memory_mode=memory_mode,
            stt_provider=stt_provider,
            stt_openai_api_key=os.getenv("COMPACK_STT_OPENAI_API_KEY"),
            stt_openai_model=stt_cfg.get("openai", {}).get("model", "whisper-1"),
            stt_local_model=stt_cfg.get("local", {}).get("model", "base"),
            llm_provider=llm_provider,
            llm_openai_api_key=os.getenv("COMPACK_LLM_OPENAI_API_KEY"),
            llm_openai_model=llm_cfg.get("openai", {}).get("model", "gpt-4"),
            llm_ollama_base_url=llm_cfg.get("ollama", {}).get("base_url", "http://localhost:11434"),
            llm_ollama_model=os.getenv("COMPACK_LLM_OLLAMA_MODEL", llm_cfg.get("ollama", {}).get("model", "")),
            llm_temperature=llm_cfg.get("openai", {}).get("temperature", 0.7),
            llm_max_tokens=llm_cfg.get("openai", {}).get("max_tokens", 1000),
            tts_provider=tts_provider,
            tts_openai_api_key=os.getenv("COMPACK_TTS_OPENAI_API_KEY"),
            tts_openai_voice=tts_cfg.get("openai", {}).get("voice", "alloy"),
            tts_openai_speed=float(tts_cfg.get("openai", {}).get("speed", 1.0)),
            tts_pyttsx3_rate=int(tts_cfg.get("pyttsx3", {}).get("rate", 150)),
            tts_pyttsx3_volume=float(tts_cfg.get("pyttsx3", {}).get("volume", 1.0)),
            session_max_context_messages=int(session_cfg.get("max_context_messages", 10)),
            log_file=log_file,
            log_level=log_level,
            audio_sample_rate=int(audio_cfg.get("sample_rate", 16000)),
            audio_channels=int(audio_cfg.get("channels", 1)),
            audio_record_duration=float(audio_cfg.get("record_duration", 5.0)),
            retry_max_attempts=int(retry_cfg.get("max_attempts", 3)),
            retry_base_delay=float(retry_cfg.get("base_delay", 1.0)),
        )

        for path in [
            config.data_dir,
            config.session_log_dir,
            config.kb_dir,
            config.uploads_dir,
            config.config_dir,
            config.data_dir / "memory",
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)
        if config.log_file:
            config.log_file.parent.mkdir(parents=True, exist_ok=True)

        return config
