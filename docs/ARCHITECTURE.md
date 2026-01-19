# Compack Architecture (Text Diagram)

## Overview
Compack is a local-first voice/text conversational agent.
It orchestrates STT/LLM/TTS and optional tools with privacy guards and external-network gating.

## High-level Components
```
User (Text/Voice)
|
v
[CLI Interface]  (apps/compack/cli/interface.py)
|  - parses commands (/help, /config, /profile, diagnose, /quit)
|  - handles session resume/new/latest
v
[Orchestrator]   (apps/compack/core/orchestrator.py)
|  - external gate (deny/ask/allow + allow_external_categories)
|  - tool-call filter / retry (tool-like JSON)
|  - PrivacyGuard (strict/normal/off)
|  - calls LLM + optional tools
v
[LLM Provider]   (Ollama local)  -> model fixed/auto-selected
|
+--> [Tools] (weather etc.)
|
v
[TTS Provider]   (pyttsx3 local)  -> voice output (optional)
|
v
User
```

## Persistence / Logs
```
apps/compack/logs/compack.log
apps/compack/logs/sessions/<session_id>.jsonl
```
- Session JSONL stores conversation turns (masked according to privacy_mode).
- Logs should never include raw secrets when privacy_mode is normal/strict.

## Security & Privacy (Local-first)
- Default: privacy_mode=normal (mask likely PII/secrets)
- strict: blocks external tool execution if PII remains
- external_network=ask: requires explicit user consent for up-to-date queries
- No background uploads; external access happens only via explicit tools after consent.
