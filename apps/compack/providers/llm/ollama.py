from __future__ import annotations

import json
from typing import AsyncIterator, Dict, List, Optional, Tuple

import requests

from apps.compack.modules.llm import LLMError, LLMProvider


class OllamaModelNotFound(LLMError):
    """Raised when a requested Ollama model is not present on the server."""


class OllamaLLM(LLMProvider):
    """Ollama ローカルモデルプロバイダ."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "", temperature: float = 0.7):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self._model_checked = False
        self._cached_tags: Optional[List[str]] = None

    async def generate(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        self.ensure_model_exists(allow_autoselect=True, raise_on_missing=True)
        payload = {"model": self.model, "messages": messages, "stream": stream, "options": {"temperature": self.temperature}}
        if stream:
            for chunk in self._stream(payload):
                yield chunk
        else:
            yield self._complete(payload)

    def ensure_model_exists(self, allow_autoselect: bool, raise_on_missing: bool) -> Dict[str, object]:
        """Verify the configured model and optionally auto-select one if missing."""
        tags = self._load_tags()
        info = {"auto_selected": False, "model_exists": True, "models": tags}
        if not tags:
            if raise_on_missing:
                raise LLMError("Ollama tags could not be retrieved.")
            info["model_exists"] = False
            return info

        if self.model:
            if self.model not in tags:
                info["model_exists"] = False
                if raise_on_missing:
                    preview = ", ".join(tags[:5])
                    more = "" if len(tags) <= 5 else f" ... (+{len(tags) - 5} more)"
                    raise OllamaModelNotFound(
                        f"Ollama model '{self.model}' not found. Available models: {preview}{more}. "
                        "Update config.yaml or COMPACK_LLM_OLLAMA_MODEL (e.g., qwen2.5-coder:7b). "
                        "Check with: ollama list"
                    )
                return info
            self._model_checked = True
            return info

        if allow_autoselect:
            self.model = self._choose_preferred_model(tags)
            info["auto_selected"] = True
            self._model_checked = True
        return info

    def _load_tags(self) -> List[str]:
        if self._cached_tags is not None:
            return self._cached_tags
        resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json() or {}
        models = []
        for entry in data.get("models", []):
            name = entry.get("name")
            if name:
                models.append(name)
        self._cached_tags = models
        return models

    @staticmethod
    def _choose_preferred_model(models: List[str]) -> str:
        preferred = ["hhao/qwen2.5-coder-tools:7b", "qwen2.5-coder:7b", "qwen2.5:7b"]
        for cand in preferred:
            if cand in models:
                return cand
        return models[0]

    def _stream(self, payload: dict) -> AsyncIterator[str]:
        with requests.post(f"{self.base_url}/api/chat", json=payload, stream=True, timeout=30) as resp:
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                self._raise_detailed_error(resp, exc)
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                message = data.get("message", {})
                content = message.get("content") or data.get("response")
                if content:
                    yield content

    def _complete(self, payload: dict) -> str:
        payload["stream"] = False
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            self._raise_detailed_error(response, exc)
        data = response.json()
        message = data.get("message", {})
        return message.get("content") or data.get("response", "")

    def should_call_tool(self, response: dict) -> Tuple[bool, Optional[dict]]:
        return False, None

    def _raise_detailed_error(self, response: requests.Response, exc: Exception) -> None:
        body: str
        try:
            body_json = response.json()
            body = json.dumps(body_json)[:500]
        except Exception:
            body = (response.text or "")[:500]
        raise LLMError(f"Ollama chat failed (status {response.status_code}): {body}") from exc

    @staticmethod
    def fetch_version(base_url: str) -> Optional[str]:
        resp = requests.get(f"{base_url.rstrip('/')}/api/version", timeout=5)
        resp.raise_for_status()
        data = resp.json() or {}
        return data.get("version")

    @staticmethod
    def fetch_tags(base_url: str) -> List[str]:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        resp.raise_for_status()
        payload = resp.json() or {}
        tags = []
        for entry in payload.get("models", []):
            if entry.get("name"):
                tags.append(entry["name"])
        return tags
