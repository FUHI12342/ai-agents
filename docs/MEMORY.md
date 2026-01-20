# Compack Memory (PR2 draft)

## Overview
- Stores lightweight conversation memory in a local JSONL file.
- Location: `<data_dir>/memory/memory.jsonl` (default `%LOCALAPPDATA%/Compack/memory/memory.jsonl` on Windows).
- Never committed to Git; `.gitignore` blocks `memory.jsonl` and `data/memory/`.

## Modes
- `manual` (default): memory is written only when explicitly added via `/memory add`.
- `auto` (planned): after each exchange, user/assistant turns are appended automatically. When assembling prompts, the most recent turn is excluded to avoid self-reference.

## Format
Each line in `memory.jsonl` is a JSON object:
```json
{"role": "user", "content": "prefers concise answers", "ts": "2024-01-20T12:34:56Z", "metadata": {"persona": "dev"}}
```

## CLI
- `/memory status` : show count and latest timestamp.
- `/memory add <text>` : append a manual note.
- `/memory show [n]` : show the latest n entries (default 5).

## Prompt injection (skeleton)
- When a memory summary exists, it is injected into the system prompt ahead of persona instructions.
- In `auto` mode, summary excludes the latest turn to avoid echoing the just-entered text.
