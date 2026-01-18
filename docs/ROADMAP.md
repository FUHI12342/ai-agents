# Compack Roadmap

## P0 (This PR)
- worktree-safe implementation (apps/compack + docs + scripts only)
- privacy_mode: strict/normal/off
- PrivacyGuard at input/log/session/tool boundaries
- diagnose: GPU usage estimation (ollama ps + nvidia-smi)
- docs: ARCHITECTURE / DATA_FLOW / ROADMAP
- scripts: git_verify.ps1, create_shortcuts.ps1
- README update (quickstart + GPU verify + shortcut guide)

## P1 (Next)
- Multi-profile (方式A) completion:
  - profiles/*.yml (name, persona/system_prompt, voice, model override)
  - CLI: /profile create/edit/delete, --profile on startup
- Local-only personal tools:
  - summarize_text_file tool (allow_paths + size limit)
  - local knowledge base ingestion (opt-in)
- UI enhancements:
  - tray/launcher GUI (start/stop, profile switch, quick commands)
  - hotkey / voice-name wake routing (future)
- Stronger privacy:
  - regex + entropy-based secret detection
  - clipboard safety mode (optional)
  - export scrubber for logs/session sharing
