import pytest

from apps.compack.utils.diagnostics import estimate_gpu_usage, parse_nvidia_smi, parse_ollama_ps


@pytest.mark.unit
def test_parse_ollama_ps_extracts_processor() -> None:
    sample = """NAME            ID              SIZE    PROCESSOR   STARTED
llama3:8b       123             4.0GB   GPU         2 minutes ago
"""
    entries = parse_ollama_ps(sample)
    assert entries[0]["name"] == "llama3:8b"
    assert entries[0]["processor"] == "GPU"


@pytest.mark.unit
def test_parse_nvidia_smi_process_detection() -> None:
    sample = """
+-----------------------------------------------------------------------------+
| Processes:                                                      GPU Memory |
|  GPU       PID   Type   Process name                             Usage      |
|=============================================================================|
|    0     12345      C   ollama.exe                                1024MiB |
+-----------------------------------------------------------------------------+
"""
    info = parse_nvidia_smi(sample)
    assert info["processes"]


@pytest.mark.unit
def test_estimate_gpu_usage_prefers_ollama_ps_gpu() -> None:
    entries = [{"name": "llama", "processor": "GPU"}]
    estimate = estimate_gpu_usage(entries, {"processes": []})
    assert estimate["estimate"] == "likely_gpu"


@pytest.mark.unit
def test_estimate_gpu_usage_unknown_when_no_signals() -> None:
    estimate = estimate_gpu_usage([], {"processes": []})
    assert estimate["estimate"] == "unknown"
