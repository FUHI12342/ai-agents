# Data Flow (Internal / External)

## 1) Internal-only flow (default)
```
User Input
-> PrivacyGuard (mask if needed)
-> Session Store (masked JSONL)
-> Orchestrator
-> Local LLM (Ollama)
-> Response
-> (Optional) Local TTS (pyttsx3)
```
- No network required.
- Logs and session files contain masked content when privacy_mode=normal/strict.

## 2) External-gated flow (external_network=ask)
```
User asks "weather/news/latest" etc.
-> needs_external 判定
-> Orchestrator asks consent (yes/no)
- no: clear pending state + guidance (ask for location, etc.)
- yes: re-run original question
-> tool execution (weather)
-> return tool result (and optionally LLM follow-up)
```

## 3) Tool-call filter flow (tool-like JSON)
```
LLM output looks like {"tool": "...", ...}
-> if tool registered: execute tool
-> else: request one-time natural-language regeneration
-> if still tool-like/invalid: return short guidance to user
```

## PrivacyGuard rules (summary)
- normal: mask and proceed
- strict: mask and if still PII-like tokens remain, block external/tool call and ask user to anonymize
