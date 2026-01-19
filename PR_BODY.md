Implements Compack P0 baseline.

## Summary
- Config refactor: `privacy_mode` as `strict/normal/off`; safe list defaults; unified env/YAML loading
- New `PrivacyGuard`: masks email/phone/card/token/zip; **strict** blocks external send
- Orchestrator wiring: sanitize -> external decision -> LLM; allowed_categories gating; notice prefix
- Diagnostics: parses `ollama ps` / `nvidia-smi` to return `gpu_inference_estimate` + privacy settings report
- CLI: add `--profile`; log privacy/external/profile at startup
- Windows helpers: `Compack_Text.bat` / `.vbs`, shortcut generator, `git_verify.ps1`
- Docs: `ARCHITECTURE` / `DATA_FLOW` / `ROADMAP` + README links
- Tests updated + added (PrivacyGuard / GPU diagnostics / external allowlist)

## Tests
- `python -m pytest apps/compack/tests -q` (56 passed, 1 skipped)
- `python -m compileall apps/compack`

## Notes / Limitations
- PrivacyGuard is regex-based masking (not perfect PII detection)
- GPU estimation depends on command availability/output and may return `unknown`
