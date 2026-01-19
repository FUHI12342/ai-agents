from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple

from apps.compack.core.logger import StructuredLogger
from apps.compack.core.privacy_guard import GuardResult, PrivacyGuard
from apps.compack.core.session import SessionManager
from apps.compack.modules import LLMModule, STTModule, TTSModule, ToolManager
from apps.compack.utils import retry_async


def _parse_tool_like(text: str) -> Tuple[Optional[str], Optional[dict]]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()
    if not candidate.startswith("{"):
        return None, None
    try:
        data = json.loads(candidate)
        name = data.get("name")
        args = data.get("arguments") or data.get("args") or {}
        if isinstance(name, str):
            return name, args if isinstance(args, dict) else {}
    except Exception:
        return None, None
    return None, None


def _looks_like_code_or_path(text: str) -> bool:
    low = text.lower()
    if text.startswith("$") or low.startswith(("python ", "cd ", "invoke-restmethod")):
        return True
    if re.search(r"\$[A-Za-z_]\w*\s*=", text):
        return True
    if ":\\" in text or re.search(r"\.(ps1|txt|json|py|bat|sh)\b", low):
        return True
    return False


class ConversationOrchestrator:
    """Controls the STT -> LLM -> TTS pipeline and external-access flow."""

    def __init__(
        self,
        stt: Optional[STTModule],
        llm: LLMModule,
        tts: Optional[TTSModule],
        session: SessionManager,
        tools: ToolManager,
        logger: StructuredLogger,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        enable_voice: bool = True,
        enable_tts: bool = True,
        kb=None,
        external_mode: str = "allow",  # allow | deny | ask
        privacy_guard: Optional[PrivacyGuard] = None,
        allow_external_categories: Optional[list] = None,
        system_prompt: str = "",
        profile_name: str = "default",
    ):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.session = session
        self.tools = tools
        self.logger = logger
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.enable_voice = enable_voice and stt is not None
        self.enable_tts = enable_tts and tts is not None
        self.kb = kb
        self.external_mode = external_mode
        self.privacy_guard = privacy_guard or PrivacyGuard(mode="off")
        self.allowed_categories = set(allow_external_categories or [])
        self.system_prompt = system_prompt
        self.profile_name = profile_name

        self._external_allowed = external_mode == "allow"
        self._pending_external_confirm = False
        self._pending_external_category: Optional[str] = None
        self._pending_location_category: Optional[str] = None
        self._pending_external_text: Optional[str] = None

    async def process_voice_input(self, duration: Optional[float] = None) -> str:
        """Record -> STT -> text processing."""
        if not self.enable_voice or not self.stt:
            self.logger.warning("音声入力が無効化されているためテキストモードで続行します")
            return ""
        try:
            audio, sample_rate = self.stt.record_audio(duration or 5.0)
            text = await retry_async(
                lambda: self.stt.transcribe(audio, sample_rate),
                max_attempts=self.retry_attempts,
                base_delay=self.retry_delay,
                on_retry=lambda attempt, exc: self.logger.warning("音声認識をリトライします", attempt=attempt),
            )
            return await self.process_text_input(text)
        except Exception as exc:
            self.handle_error(exc, "voice_input")
            return ""

    def _apply_guard(self, text: str, *, for_external: bool = False) -> GuardResult:
        result = self.privacy_guard.sanitize(text, for_external=for_external)
        if result.masked:
            self.logger.info("PrivacyGuard masked input", findings=result.findings, for_external=for_external)
        return result

    async def process_text_input(self, text: str) -> str:
        """Handle text input including external confirmation and LLM/TTS."""
        guard_result = self._apply_guard(text, for_external=False)
        sanitized_text = guard_result.text

        # (1) Pending external confirmation
        if self._pending_external_confirm:
            self._pending_external_confirm = False
            if sanitized_text.strip().lower() in {"y", "yes", "はい"}:
                self._external_allowed = True
                category = self._pending_external_category
                original = self._pending_external_text or sanitized_text
                self._pending_external_category = None
                self._pending_external_text = None
                if category == "weather":
                    self._pending_location_category = "weather"
                    prompt = "地域名を教えてください（例: 東京/奈良市）"
                    self.session.add_message("assistant", prompt)
                    self.session.save_session()
                    return prompt
                return await self._process_text_with_llm(original, notice=guard_result.notice)
            self._pending_external_category = None
            self._pending_external_text = None
            guidance = "外部アクセスなしで進めます。地域名や手元の最新情報を教えていただければ要約します。"
            self.session.add_message("assistant", guidance)
            self.session.save_session()
            return guidance

        # (2) Pending location for weather
        if self._pending_location_category == "weather":
            location_result = self._apply_guard(sanitized_text, for_external=True)
            if location_result.blocked:
                self._pending_location_category = None
                self.session.add_message("assistant", location_result.notice or "")
                self.session.save_session()
                return location_result.notice or "外部送信を中止しました。"
            location = location_result.text.strip()
            if not location:
                prompt = "地域名を教えてください（例: 東京/奈良市）"
                self.session.add_message("assistant", prompt)
                self.session.save_session()
                return prompt
            self._pending_location_category = None
            return await self._handle_external_category("weather", location, notice=location_result.notice)

        # (3) New external request
        category = self._external_category(sanitized_text)
        if category:
            if self.allowed_categories and category not in self.allowed_categories:
                guidance = "このカテゴリの外部アクセスは許可されていません。匿名化した情報を直接入力してください。"
                self.session.add_message("assistant", guidance)
                self.session.save_session()
                return guidance
            if self.external_mode == "deny":
                guidance = "外部アクセスは無効です。地域名や最新情報を入力いただければ要約します。"
                self.session.add_message("assistant", guidance)
                self.session.save_session()
                return guidance
            if self.external_mode == "ask" and not self._external_allowed:
                prompt = "最新情報を取得するため外部アクセスが必要です。許可しますか？ (yes/no)"
                self._pending_external_confirm = True
                self._pending_external_category = category
                self._pending_external_text = sanitized_text
                self.session.add_message("assistant", prompt)
                self.session.save_session()
                return prompt
            if category == "weather":
                self._pending_location_category = category
                prompt = "地域名を教えてください（例: 東京/奈良市）"
                self.session.add_message("assistant", prompt)
                self.session.save_session()
                return prompt

        # (4) Normal LLM path
        return await self._process_text_with_llm(sanitized_text, notice=guard_result.notice)

    def _external_category(self, text: str) -> Optional[str]:
        if _looks_like_code_or_path(text):
            return None
        low = text.lower()
        if "天気" in text or "weather" in low:
            return "weather"
        jp_keywords = ["ニュース", "イベント", "最新"]
        if any(k in text for k in jp_keywords):
            return "general"
        boundary_words = ["latest", "news", "stock", "traffic", "nearby", "event"]
        for word in boundary_words:
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", low):
                return "general"
        return None

    async def _handle_external_category(self, category: str, location: str, notice: Optional[str] = None) -> str:
        if category == "weather":
            result = await self.tools.execute("weather", {"location": location})
            if result.success:
                data = result.result or {}
                summary = data.get("summary") or data
                message = f"{location}の天気: {summary}"
            else:
                message = f"天気取得に失敗しました: {result.error}"
            if notice:
                message = f"{notice}\n{message}"
            self.session.add_message("assistant", message)
            self.session.save_session()
            return message
        fallback = "外部アクセスなしで対応します。関連情報を教えてください。"
        self.session.add_message("assistant", fallback)
        self.session.save_session()
        return fallback

    async def _process_text_with_llm(self, text: str, notice: Optional[str] = None) -> str:
        self.session.add_message("user", text)
        context = self.session.get_context()
        rag_messages = []
        if self.kb:
            results = self.kb.search(text, top_k=3)
            if results:
                joined = "\n".join([f"- {r['match']['preview']}" for r in results])
                rag_messages.append({"role": "system", "content": f"Knowledge base:\n{joined}"})
        context = rag_messages + context
        if self.system_prompt:
            context = [{"role": "system", "content": self.system_prompt}] + context

        response_text = await self._generate_text(context)
        tool_name, tool_args = _parse_tool_like(response_text)
        if tool_name:
            if tool_name in self.tools.tools:
                result = await self.tools.execute(tool_name, tool_args or {})
                message = str(result.result or result.error or "")
                self.session.add_message("assistant", message)
                self.session.save_session()
                return message
            retry_context = context + [
                {"role": "system", "content": "ツール呼び出しのJSONは出さず、日本語の自然文で回答してください。"}
            ]
            retry_text = await self._generate_text(retry_context)
            retry_name, _ = _parse_tool_like(retry_text)
            if retry_name:
                guidance = "内部ツール形式の返答が出ました。普通の文章で言い直してください。"
                self.session.add_message("assistant", guidance)
                self.session.save_session()
                return guidance
            response_text = retry_text

        if notice:
            response_text = f"{notice}\n{response_text}"

        self.session.add_message("assistant", response_text)
        self.session.save_session()

        if self.enable_tts and self.tts:
            try:
                audio = await self.tts.synthesize(response_text)
                self.tts.play_audio(audio)
            except Exception as exc:
                self.logger.warning("音声出力に失敗しました", error=exc)

        return response_text

    async def _generate_text(self, context: list) -> str:
        response_parts = []
        try:
            async for chunk in self.llm.generate_response(context, tools=self.tools.get_tool_schemas()):
                response_parts.append(chunk)
            response_text = "".join(response_parts).strip()
        except Exception as exc:
            self.logger.error(
                "LLM生成に失敗しました",
                error=exc,
                error_type=exc.__class__.__name__,
                provider=self.llm.provider.__class__.__name__,
            )
            response_text = (
                "LLM (Ollama) に接続できない、またはモデルが見つかりません。"
                " /diagnose で確認し、/config でモデルを qwen2.5-coder:7b などに変更してください。"
            )
        return response_text

    async def execute_tool(self, tool_name: str, args: Dict) -> Dict:
        """Execute a registered tool and record the result."""
        result = await self.tools.execute(tool_name, args)
        self.session.add_message(
            "tool",
            str(result.result or result.error),
            metadata={"tool": tool_name, "success": result.success},
        )
        self.session.save_session()
        return result.to_dict()

    def handle_error(self, error: Exception, context: str) -> None:
        self.logger.error("処理中にエラーが発生しました", error=error, context=context)
