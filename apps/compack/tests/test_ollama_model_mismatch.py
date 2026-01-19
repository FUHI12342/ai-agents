import pytest

from apps.compack.providers.llm.ollama import OllamaLLM, OllamaModelNotFound


def test_model_mismatch_raises_not_found(monkeypatch):
    provider = OllamaLLM(base_url="http://localhost:11434", model="missing")
    monkeypatch.setattr(provider, "_load_tags", lambda: ["qwen2.5-coder:7b", "other"])

    with pytest.raises(OllamaModelNotFound) as exc:
        provider.ensure_model_exists(allow_autoselect=False, raise_on_missing=True)

    msg = str(exc.value)
    assert "missing" in msg
    assert "qwen2.5-coder:7b" in msg
    assert "ollama list" in msg
