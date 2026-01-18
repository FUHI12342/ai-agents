import pytest

from apps.compack.core import ConfigManager
from apps.compack.utils import run_diagnostics


@pytest.mark.unit
def test_diagnostics_reports_ollama(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.compack.utils.diagnostics.OllamaLLM.fetch_version", lambda base: "0.13.5")
    monkeypatch.setattr(
        "apps.compack.utils.diagnostics.OllamaLLM.fetch_tags",
        lambda base: ["qwen2.5-coder:7b", "hhao/qwen2.5-coder-tools:7b"],
    )
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
llm:
  provider: ollama
  ollama:
    base_url: http://localhost:11434
    model: qwen2.5-coder:7b
""",
        encoding="utf-8",
    )
    manager = ConfigManager(env_path=tmp_path / ".env", config_path=cfg_path)
    report = run_diagnostics(manager, mode="text")

    assert report["ollama"]["reachable"] is True
    assert report["ollama"]["version"] == "0.13.5"
    assert "qwen2.5-coder:7b" in report["ollama"]["models"]
    assert report["ollama"]["model_exists"] is True
    assert not report["warnings"]


@pytest.mark.unit
def test_diagnostics_warns_on_missing_model(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.compack.utils.diagnostics.OllamaLLM.fetch_version", lambda base: "0.13.5")
    monkeypatch.setattr("apps.compack.utils.diagnostics.OllamaLLM.fetch_tags", lambda base: ["other"])
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
llm:
  provider: ollama
  ollama:
    base_url: http://localhost:11434
    model: missing
""",
        encoding="utf-8",
    )
    manager = ConfigManager(env_path=tmp_path / ".env", config_path=cfg_path)
    report = run_diagnostics(manager, mode="text")

    assert report["ollama"]["model_exists"] is False
    assert any("Ollama model is not available" in w for w in report["warnings"])
