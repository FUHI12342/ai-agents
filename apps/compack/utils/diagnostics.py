from __future__ import annotations

import importlib.util
import subprocess
from typing import Any, Dict, List

from apps.compack.core import ConfigManager
from apps.compack.providers.llm.ollama import OllamaLLM


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _audio_devices() -> Dict[str, Any]:
    if not _module_available("sounddevice"):
        return {"available": False, "reason": "sounddevice not installed"}
    try:
        import sounddevice as sd  # type: ignore

        devices = []
        for device in sd.query_devices():
            devices.append(
                {
                    "name": device["name"],
                    "max_input_channels": device["max_input_channels"],
                    "max_output_channels": device["max_output_channels"],
                }
            )
        return {"available": True, "devices": devices}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"available": False, "reason": str(exc)}


def _playback_status() -> Dict[str, Any]:
    if _module_available("pygame"):
        return {"available": True, "module": "pygame"}
    if _module_available("pyttsx3"):
        return {"available": True, "module": "pyttsx3"}
    return {"available": False, "reason": "pygame/pyttsx3 not installed"}


def _env_requirements(cfg) -> List[str]:
    missing: List[str] = []
    if cfg.llm_provider == "openai_gpt4" and not cfg.llm_openai_api_key:
        missing.append("COMPACK_LLM_OPENAI_API_KEY is required for openai_gpt4")
    if cfg.stt_provider == "openai_whisper" and not cfg.stt_openai_api_key:
        missing.append("COMPACK_STT_OPENAI_API_KEY is required for openai_whisper")
    if cfg.tts_provider == "openai_tts" and not cfg.tts_openai_api_key:
        missing.append("COMPACK_TTS_OPENAI_API_KEY is required for openai_tts")
    return missing


def _run_cmd(cmd: List[str]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "success": completed.returncode == 0,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "returncode": completed.returncode,
        }
    except FileNotFoundError:
        return {"success": False, "error": "command_not_found"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"success": False, "error": str(exc)}


def parse_ollama_ps(stdout: str) -> List[Dict[str, str]]:
    """Parse `ollama ps` output into a list of {name, processor} entries."""
    entries: List[Dict[str, str]] = []
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if len(lines) <= 1:
        return entries
    for line in lines[1:]:
        parts = [p for p in line.split(" ") if p]
        if len(parts) < 4:
            continue
        name = parts[0]
        processor = parts[3] if len(parts) >= 4 else parts[-1]
        entries.append({"name": name, "processor": processor})
    return entries


def parse_nvidia_smi(stdout: str) -> Dict[str, Any]:
    """Parse a minimal subset of `nvidia-smi` output."""
    info: Dict[str, Any] = {"gpus": [], "processes": []}
    lines = stdout.splitlines()
    for line in lines:
        if "MiB |" in line and "%" in line and "Default" in line:
            info["gpus"].append(line.strip())
        if "Processes" in line:
            # the following lines list processes; we just collect raw lines for display
            continue
        if "ollama" in line.lower():
            info["processes"].append(line.strip())
    return info


def estimate_gpu_usage(ollama_entries: List[Dict[str, str]], nvidia_info: Dict[str, Any]) -> Dict[str, str]:
    likely = "unknown"
    rationale = []
    for entry in ollama_entries:
        proc = entry.get("processor", "").lower()
        if any(k in proc for k in ["gpu", "cuda", "metal"]):
            likely = "likely_gpu"
            rationale.append(f"ollama processor={entry.get('processor')}")
            break
        if "cpu" in proc:
            likely = "likely_cpu"
            rationale.append("ollama reports cpu")
    if nvidia_info.get("processes"):
        likely = "likely_gpu"
        rationale.append("nvidia-smi shows ollama process")
    return {"estimate": likely, "rationale": "; ".join(rationale) or "no signals"}


def _ollama_info(cfg) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "reachable": False,
        "version": None,
        "models": [],
        "configured_model": cfg.llm_ollama_model,
        "model_exists": True,
    }
    if cfg.llm_provider != "ollama":
        info["skipped"] = True
        info["model_exists"] = False
        return info

    base = cfg.llm_ollama_base_url
    try:
        version = OllamaLLM.fetch_version(base)
        info["version"] = version
        info["reachable"] = True
    except Exception as exc:  # pragma: no cover - network variability
        info["error"] = str(exc)
        info["model_exists"] = False
        return info

    try:
        tags = OllamaLLM.fetch_tags(base)
        info["models"] = tags
        if cfg.llm_ollama_model:
            info["model_exists"] = cfg.llm_ollama_model in tags
    except Exception as exc:  # pragma: no cover - network variability
        info["error"] = str(exc)
        info["model_exists"] = False
    return info


def _ollama_ps_info() -> Dict[str, Any]:
    result = _run_cmd(["ollama", "ps"])
    parsed = parse_ollama_ps(result.get("stdout", ""))
    return {"raw": result, "entries": parsed}


def _nvidia_smi_info() -> Dict[str, Any]:
    result = _run_cmd(["nvidia-smi"])
    if not result.get("success") and result.get("error") == "command_not_found":
        return {"available": False, "reason": "nvidia-smi not found"}
    parsed = parse_nvidia_smi(result.get("stdout", ""))
    return {"available": result.get("success", False), "raw": result, "parsed": parsed}


def run_diagnostics(config_manager: ConfigManager, mode: str = "text") -> Dict[str, Any]:
    cfg = config_manager.config or config_manager.load()
    warnings: List[str] = []

    ollama_info = _ollama_info(cfg)
    if not ollama_info.get("model_exists", True) and cfg.llm_provider == "ollama":
        warnings.append("Ollama model is not available on the server. Run 'ollama list' and update config.")

    ollama_ps = _ollama_ps_info()
    nvidia_smi = _nvidia_smi_info()
    gpu_estimate = estimate_gpu_usage(ollama_ps.get("entries", []), nvidia_smi.get("parsed", {}))

    return {
        "mode": mode,
        "providers": {
            "stt": cfg.stt_provider,
            "llm": cfg.llm_provider,
            "tts": cfg.tts_provider,
        },
        "env_missing": _env_requirements(cfg),
        "dependencies": {
            "sounddevice": _module_available("sounddevice"),
            "soundfile": _module_available("soundfile"),
            "pygame": _module_available("pygame"),
            "pyttsx3": _module_available("pyttsx3"),
            "whisper": _module_available("whisper"),
        },
        "audio_devices": _audio_devices() if mode == "voice" else {"skipped": True},
        "playback": _playback_status(),
        "privacy_mode": cfg.privacy_mode,
        "external_network": cfg.external_network,
        "allow_external_categories": cfg.allow_external_categories,
        "allow_paths": cfg.allow_paths,
        "profile_name": getattr(cfg, "profile_name", "default"),
        "ollama": ollama_info,
        "ollama_ps": ollama_ps,
        "nvidia_smi": nvidia_smi,
        "gpu_inference_estimate": gpu_estimate,
        "warnings": warnings,
    }
