# GPU Verification (Windows, Ollama)

This guide helps you confirm that RTX/GPU is actually used by Ollama (and Compack).

## Prerequisites
- NVIDIA GPU + driver installed
- `nvidia-smi` available in PowerShell
- Ollama running locally (e.g., `ollama run llama3` works)

## Quick check
```powershell
nvidia-smi
```
You should see your GPU listed. If this fails, install/update the NVIDIA driver.

## Live monitoring while running Ollama/Compack
1) Start monitoring in a separate PowerShell window:
```powershell
nvidia-smi -l 1
```
2) In another window, run a model (or start Compack):
```powershell
# Minimal model test
ollama run llama3

# Or start Compack (text mode)
python -m apps.compack.main --mode text --resume new
```
3) Watch `nvidia-smi` output:
   - `GPU-Util` rises above 0%
   - `Memory-Usage` increases
   - In the `Processes` section, `ollama.exe` shows up (Type=C on WDDM).

## Notes for WDDM users
- On some Windows setups, the per-process GPU memory column can show `N/A`.
- If `Memory-Usage` stays `N/A`, use these signals instead:
  - `GPU-Util` spikes when a prompt runs
  - `Power Draw` increases
  - `P-state` shifts from P8/P12 to an active state (e.g., P2)

If none of the above changes occur, Ollama might be falling back to CPU; verify your model/driver install.
