# RAG / KB (PR3 skeleton)

## Overview
- Persona-aware KB stored under `<data_dir>/kb/<persona>/`.
- Retrieval is lightweight token overlap (no vector DB yet). This is a PR3 scaffold.
- Retrieval order inside system prompt:
  1) Base policy + profile
  2) Memory Summary (if any)
  3) Retrieved Context (this KB result)
  4) Persona prompt

## Persona-specific layout
```
<data_dir>/kb/default/kb_index.jsonl
<data_dir>/kb/dev/kb_index.jsonl
...
```
- Search prefers the current persona's KB; if missing/empty, falls back to `default`.

## Commands (CLI)
- `/kb status` : show entry counts per persona.
- `/kb add <path> [persona]` : ingest file/dir into the given persona (defaults to current persona).
- Files supported: `.txt`, `.md`, `.json`, `.pdf` (PDF requires PyPDF2).

## Privacy / Git hygiene
- KB content stays local. `**/data/kb/**` is ignored in Git.
- Do not commit real documents; use `.gitkeep` only if needed.
