# Dev Environment Setup (ai-agents-dev)

## Quick Start
```powershell
cd C:\Users\FHiro\Projects\ai-agents-dev
$env:ENV = "dev"
$env:TRADER_DOTENV_PATH = ".env.dev"
$env:TRADER_EXCHANGE_ENV = "testnet"
```

## Daily dev run (paper mode)
```powershell
if (Test-Path .\.venv\Scripts\Activate.ps1) { . .\.venv\Scripts\Activate.ps1 }
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_dev_daily_task.ps1
```
What happens:
- Task wrapper sets core env (dev/paper/testnet/allowlist, UTF-8, dev data/log/reports/state paths), loads `scripts/secrets.local.ps1` if present, then calls `scripts/run_dev_daily.ps1`.
- `run_dev_daily.ps1`:
  - Determines eval_days (3–7) via `trader.ops_window` from `daily_*.json` coverage. If <3, skips scoring/gate/notify and exits 0.
  - Runs paper daily placeholder (no live orders).
  - Runs `trader.ops_scorecard` (auto threshold scaling) -> writes `reports/ops_scorecard_*.{json,txt}`.
  - If score PASS, runs `trader.ops_gate` -> writes `reports/ops_gate_*.{json,txt}`.
  - Always writes `reports/ops_autorun_latest.json` (eval_days, coverage, score/gate outcomes, notify flags).
  - If score & gate both PASS, runs `trader.ops_notify` once per day (Gmail if configured, otherwise log notification; non-fatal).
  - Always writes `reports/ops_heartbeat_latest.json` for observability.
  - Logs transcript to `D:\ai-data\trader-dev\logs\run_dev_daily_*.log`.

## Ops notify Gmail send (dev)
- Copy `scripts\secrets.local.ps1.example` to `scripts\secrets.local.ps1` and fill the GMAIL_* values (keep this file and `.secrets/` out of git).
- Env vars (per session or via `scripts/secrets.local.ps1` loaded by wrappers):
  - `GMAIL_SENDER`, `GMAIL_TO`
  - `GMAIL_CREDENTIALS_PATH` (e.g. `C:\Users\FHiro\Projects\ai-agents-dev\.secrets\gmail\credentials.json`)
  - `GMAIL_TOKEN_PATH` (e.g. `C:\Users\FHiro\Projects\ai-agents-dev\.secrets\gmail\token.json`)
- First-time token (browser auth):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_gmail_token.ps1
```
- Send test:
```powershell
python -m trader.notify.gmail_sender --sender $env:GMAIL_SENDER --to $env:GMAIL_TO `
  --credentials $env:GMAIL_CREDENTIALS_PATH --token $env:GMAIL_TOKEN_PATH `
  --subject "TRADER notify test" --body "hello"
```
- `trader.ops_notify` falls back to log notification if Gmail is not configured and prevents multiple sends per day. Keep `.secrets/` out of git.

## Task Scheduler (Windows)
- Action: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\FHiro\Projects\ai-agents-dev\scripts\run_dev_daily_task.ps1`
- Start in: `C:\Users\FHiro\Projects\ai-agents-dev`
- Run daily at desired time. Ensure token is created once via `init_gmail_token.ps1` before scheduling.

## Notes
- Work only in `ai-agents-dev` for dev tasks; production repo (`ai-agents`) remains untouched.
- Keep `.secrets/`, credentials.json, token.json, and `scripts/secrets.local.ps1` out of git (ignored). 
