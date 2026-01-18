# Compack (魂魄) MVP

Local-first voice/chat agent with optional cloud providers, privacy controls, and a minimal web UI.

## Quick Start
1) Python 3.11+ and a virtualenv in the repo root (`.venv` recommended)  
2) Install the core deps: `pip install -r requirements.txt`  
3) Copy `.env.example` to `.env` and set OpenAI keys only if you plan to use OpenAI providers  
4) Run the text-safe entrypoint:  
```bash
python -m apps.compack.main --mode text
```

## Web UI
- Install extras:  
  - Audio I/O: `pip install -r requirements-audio.txt`  
  - pyttsx3 (local TTS): `pip install -r requirements-tts.txt`  
  - Local Whisper: `pip install -r requirements-whisper.txt`  
- Web UI: `pip install -r requirements-web.txt`  
- Launch: `python -m apps.compack.main --mode voice --ui web --open-browser`  
- Ollama model: leave `config.yaml` model blank to auto-pick from installed tags; commonly `qwen2.5-coder:7b`.
- Shortcut launch (text, always new session): `python -m apps.compack.main --mode text --resume new`

## 実機確認（Windows + Ollama）
- Ollama起動確認:  
  - `Invoke-RestMethod http://localhost:11434/api/version`  
  - `ollama list`
- Compack最短起動（モデル自動選択）:  
  - `python -m apps.compack.main --mode text --resume new`
- モデルを固定したい場合（例: qwen2.5-coder:7b）:  
  - PowerShell: `$env:COMPACK_LLM_OLLAMA_MODEL="qwen2.5-coder:7b"` then run the command above
- 診断:  
  - `python -m apps.compack.main --diagnose --mode text`
- デスクトップショートカット作成: `Compack_Text.bat` をデスクトップにコピーしてダブルクリック（`.venv` があれば自動で有効化し新規セッションで起動）

## Diagnostics
```bash
python -m apps.compack.main --diagnose --mode voice
```
Lists audio devices, optional dependencies, chosen providers, and missing env vars.

## Local KB (RAG)
- Ingest: `python -m apps.compack.main kb add <path>` (.txt/.md/.json/.pdf)  
- Status: `python -m apps.compack.main kb status`  
- RAG is used automatically when the KB exists; privacy settings still apply.

## Privacy Mode
- `config.yaml` → `privacy.enabled` (default true) and `external: deny|allow|ask`  
- `deny` blocks OpenAI providers; `ask` prompts once per run; `allow` permits calls.

## Data Locations
- Default root: `%LOCALAPPDATA%\Compack\` on Windows, `~/.compack/` on macOS/Linux  
- Override: `COMPACK_DATA_DIR`  
- Subfolders: `sessions/` (JSONL logs), `kb/`, `uploads/`, `config/`

## Windows Shortcut
1) Run `apps/compack/scripts/windows/setup_windows.ps1` to create `.venv` and install deps  
2) Run `apps/compack/scripts/windows/create_desktop_shortcut.ps1` to drop `Compack.lnk` on the desktop  
3) Double-click the shortcut to start the web UI (`fastapi/uvicorn` required)

## Testing
```bash
pip install -r requirements-dev.txt
pytest apps/compack/tests
```

## Known Optional Pieces
- fastapi/uvicorn, sounddevice, pyttsx3, and whisper are optional; install the matching extras when you need web UI, audio I/O, or TTS/STT.  
- OpenAI keys are only required when selecting OpenAI providers.
