## Windows Task Scheduler Setup (dev, paper-only)

1) Program/script: `powershell.exe`
2) Arguments: `-NoProfile -ExecutionPolicy Bypass -File C:\Users\FHiro\Projects\ai-agents-dev\scripts\run_dev_daily_task.ps1`
3) Start in: `C:\Users\FHiro\Projects\ai-agents-dev`
4) Run daily at desired time; enable “run with highest privileges” if needed.
5) Ensure Gmail token is created once (manual browser auth):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_gmail_token.ps1
```
6) Secrets/environment: copy `scripts\secrets.local.ps1.example` to `scripts\secrets.local.ps1`, fill GMAIL_* values, and keep `.secrets/` + credentials/token files out of git.
7) Outputs to watch:
   - `reports/ops_autorun_latest.json` (eval_days, score/gate/notify outcomes)
   - `reports/ops_heartbeat_latest.json` (last run timestamps and status)
   - Logs: `D:\ai-data\trader-dev\logs\run_dev_daily_*.log`

Notes:
- Pipeline stays in paper mode; no live orders are sent.
- If Gmail is not configured or sending fails, notification falls back to log and the job continues.
