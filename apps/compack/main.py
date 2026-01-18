from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from apps.compack.cli.interface import CLIInterface
from apps.compack.core import ConfigManager, ConversationOrchestrator, KBManager, SessionManager, StructuredLogger
from apps.compack.core.privacy_guard import PrivacyGuard
from apps.compack.models import Config
from apps.compack.modules import LLMModule, STTModule, TTSModule, ToolManager
from apps.compack.providers.llm import OllamaLLM, OpenAIGPT4LLM
from apps.compack.providers.stt import LocalWhisperSTT, OpenAIWhisperSTT
from apps.compack.providers.tts import OpenAITTSTTS, Pyttsx3TTS
from apps.compack.tools import SaveMemoTool, SearchFilesTool, SetTimerTool, WeatherTool
from apps.compack.utils.diagnostics import run_diagnostics
from apps.compack.ui.web import start_web_ui


def build_logger(config_manager: ConfigManager) -> StructuredLogger:
    config = config_manager.config or config_manager.load()
    return StructuredLogger(log_file=config.log_file, level=config.log_level)


def _check_external_permission(config: Config) -> bool:
    if config.external_network == "allow":
        return True
    if config.external_network == "deny":
        return False
    if config.external_network == "ask":
        answer = input("外部サービスへの送信を許可しますか？ [y/N]: ").strip().lower()
        return answer in ("y", "yes")
    return False


def build_stt(config: Config, logger: StructuredLogger) -> Optional[STTModule]:
    try:
        if config.stt_provider == "openai_whisper":
            if not _check_external_permission(config):
                raise RuntimeError("外部送信が拒否されました。ローカルSTTを使用してください。")
            provider = OpenAIWhisperSTT(api_key=config.stt_openai_api_key, model=config.stt_openai_model)
        else:
            provider = LocalWhisperSTT(model_name=config.stt_local_model)
        return STTModule(provider=provider, logger=logger, sample_rate=config.audio_sample_rate, channels=config.audio_channels)
    except Exception as exc:  # pragma: no cover - optional dependency guard
        logger.warning("STT初期化に失敗しました。音声モードを無効化します。", error=exc)
        return None


def build_llm(config: Config, logger: StructuredLogger) -> LLMModule:
    if config.llm_provider == "openai_gpt4":
        if not _check_external_permission(config):
            raise RuntimeError("外部送信が拒否されました。ローカルLLMを使用してください。")
        provider = OpenAIGPT4LLM(
            api_key=config.llm_openai_api_key,
            model=config.llm_openai_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )
    else:
        provider = OllamaLLM(base_url=config.llm_ollama_base_url, model=config.llm_ollama_model, temperature=config.llm_temperature)
        try:
            info = provider.ensure_model_exists(allow_autoselect=True, raise_on_missing=False)
            if info.get("auto_selected"):
                logger.info("Ollama model auto-selected", model=provider.model)
            elif not info.get("model_exists", True):
                logger.warning("Ollama model not found; will error on first call", model=config.llm_ollama_model)
        except Exception as exc:  # pragma: no cover - optional network issues
            logger.warning("Ollama model pre-check failed", error=exc)
    return LLMModule(provider=provider, logger=logger, max_context_messages=config.session_max_context_messages)


def build_tts(config: Config, logger: StructuredLogger) -> Optional[TTSModule]:
    try:
        if config.tts_provider == "openai_tts":
            if not _check_external_permission(config):
                raise RuntimeError("外部送信が拒否されました。ローカルTTSを使用してください。")
            provider = OpenAITTSTTS(api_key=config.tts_openai_api_key, voice=config.tts_openai_voice, speed=config.tts_openai_speed)
        else:
            provider = Pyttsx3TTS(rate=config.tts_pyttsx3_rate, volume=config.tts_pyttsx3_volume)
        return TTSModule(provider=provider, logger=logger)
    except Exception as exc:  # pragma: no cover - optional dependency guard
        logger.warning("TTS初期化に失敗しました。音声出力を無効化します。", error=exc)
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compack (魂魄) CLI")
    parser.add_argument("--mode", choices=["text", "voice"], default="text", help="text: 音声依存なし / voice: 音声入出力")
    parser.add_argument("--diagnose", action="store_true", help="環境診断を実行して終了")
    parser.add_argument("--config", type=str, help="config.yaml のパスを上書き")
    parser.add_argument("--env", type=str, help=".env のパスを上書き")
    parser.add_argument("--ui", choices=["cli", "web"], default="cli", help="CLI or ローカルWeb UIを選択")
    parser.add_argument("--open-browser", action="store_true", help="Web UI起動時にブラウザを開く")
    parser.add_argument("--resume", type=str, help="セッション再開モード new/latest/<id>")
    parser.add_argument("--profile", type=str, help="プロファイル名を上書き")

    sub = parser.add_subparsers(dest="subcommand")
    kb = sub.add_parser("kb", help="ローカルKB操作")
    kb.add_argument("action", choices=["add", "status"])
    kb.add_argument("path", nargs="?", help="取り込みファイル/ディレクトリ (add時必須)")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config_manager = ConfigManager(env_path=args.env, config_path=args.config)
    config = config_manager.load()
    if args.profile:
        config.profile_name = args.profile

    if args.subcommand == "kb":
        logger = StructuredLogger(log_file=None, level="INFO")
        kb = KBManager(config.kb_dir)
        if args.action == "add":
            if not args.path:
                print("パスを指定してください: compack kb add <path>")
                sys.exit(1)
            added = kb.add_path(Path(args.path))
            print(f"追加完了: {added} 件")
        else:
            print(json.dumps(kb.status(), ensure_ascii=False, indent=2))
        return

    if args.diagnose:
        report = run_diagnostics(config_manager, mode=args.mode)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    errors = config_manager.validate(mode=args.mode)
    if errors:
        print("設定エラーが見つかりました。")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)

    logger = build_logger(config_manager)
    logger.info(
        "起動設定",
        mode=args.mode,
        stt=config.stt_provider,
        llm=config.llm_provider,
        tts=config.tts_provider,
        log_file=str(config.log_file) if config.log_file else None,
        privacy_mode=config.privacy_mode,
        external_network=config.external_network,
        profile=config.profile_name,
    )

    session = SessionManager(log_dir=config.session_log_dir, logger=logger, max_context_messages=config.session_max_context_messages)
    llm = build_llm(config, logger)
    stt = build_stt(config, logger) if args.mode == "voice" else None
    tts = build_tts(config, logger) if args.mode == "voice" else None
    kb_manager = KBManager(config.kb_dir)
    privacy_guard = PrivacyGuard(mode=config.privacy_mode, allow_paths=config.allow_paths)

    tools = ToolManager(logger=logger)
    tools.register(SaveMemoTool())
    tools.register(SetTimerTool())
    tools.register(SearchFilesTool())
    tools.register(WeatherTool())

    orchestrator = ConversationOrchestrator(
        stt=stt,
        llm=llm,
        tts=tts,
        session=session,
        tools=tools,
        logger=logger,
        retry_attempts=config.retry_max_attempts,
        retry_delay=config.retry_base_delay,
        enable_voice=args.mode == "voice",
        enable_tts=args.mode == "voice",
        kb=kb_manager,
        external_mode=config.external_network,
        privacy_guard=privacy_guard,
        allow_external_categories=config.allow_external_categories,
        system_prompt=config.system_prompt,
        profile_name=config.profile_name,
    )
    if args.ui == "web":
        start_web_ui(orchestrator, host="127.0.0.1", port=8765, open_browser=args.open_browser)
    else:
        cli = CLIInterface(orchestrator, config_manager)
        await cli.start(mode=args.mode, resume=args.resume)


if __name__ == "__main__":
    asyncio.run(main())
