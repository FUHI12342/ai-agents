import json

import pytest

from apps.compack.core import ConfigManager
from apps.compack.utils import run_diagnostics


@pytest.mark.unit
def test_diagnostics_shapes(tmp_path, monkeypatch) -> None:
    for key in ["COMPACK_STT_PROVIDER", "COMPACK_LLM_PROVIDER", "COMPACK_TTS_PROVIDER"]:
        monkeypatch.delenv(key, raising=False)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        """
stt:
  provider: openai_whisper
llm:
  provider: openai_gpt4
tts:
  provider: openai_tts
""",
        encoding="utf-8",
    )
    manager = ConfigManager(env_path=tmp_path / ".env", config_path=cfg_path)
    report = run_diagnostics(manager, mode="text")
    assert report["providers"]["llm"] == "openai_gpt4"
    assert "env_missing" in report
    assert "dependencies" in report
    assert report["audio_devices"]["skipped"]
    assert "gpu_inference_estimate" in report
    assert "privacy_mode" in report
