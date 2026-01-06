"""
Report blocks for email notifications.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import json
import datetime
import platform
from pathlib import Path
import glob
import re

from .config import load_config


def render_min_lot_live_gonogo_email() -> str:
    """
    Render the full Go/No-Go checklist template with placeholders replaced.
    """
    config = load_config()
    base_dir = Path(__file__).parent.parent / "reports"

    # Helper functions
    def get_latest_file(pattern: str, directory: Path) -> Optional[Path]:
        if not directory.exists():
            return None
        files = list(directory.glob(pattern))
        if not files:
            return None
        return max(files, key=lambda x: x.stat().st_mtime)

    # Collect data
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    hostname = platform.node()

    # Logs
    logs_dir = Path(__file__).parent.parent / "scripts" / "logs"
    latest_daily_log = get_latest_file("daily_run_*.log", logs_dir)

    go_nogo_latest = base_dir / "go_nogo_latest.txt"
    paper_state = Path(r"D:\ai-data\paper_state.json")
    live_ledgers = list(base_dir.glob("live_*history*.csv"))
    reconcile_latest = base_dir / "reconcile_latest.json"

    # Config values
    trader_mode = config.trader_mode
    dry_run = config.dry_run
    kill_switch = config.kill_switch_path.exists()
    live_confirm = config.trader_live_confirm
    armed = config.is_live_armed
    api_configured = config.is_api_configured()

    # Log checks
    lock_acquired = False
    ops_cleanup = False
    if latest_daily_log and latest_daily_log.exists():
        with open(latest_daily_log, 'r', encoding='utf-8') as f:
            log_content = f.read()
        lock_acquired = "[GUARD] lock acquired:" in log_content and "[GUARD] lock released:" in log_content
        ops_cleanup = "[STEP] ops_cleanup" in log_content and "[GUARD] ops_cleanup done" in log_content

    lock_acquired_text = "PASS" if lock_acquired else "FAIL"
    ops_cleanup_text = "PASS" if ops_cleanup else "FAIL"

    # Reconcile data
    reconcile_exists = reconcile_latest.exists()
    reconcile_ok = False
    if reconcile_exists:
        try:
            with open(reconcile_latest, 'r', encoding='utf-8') as f:
                data = json.load(f)
            reconcile_ok = data.get("ok", False)
        except:
            pass

    # Live summary reconcile_ok
    live_summary_reconcile_ok = None
    live_summary_latest = base_dir / "live_summary_latest.txt"
    if live_summary_latest.exists():
        with open(live_summary_latest, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'reconcile_ok:\s*(true|false|None)', content, re.IGNORECASE)
            if match:
                val = match.group(1).lower()
                if val == 'true':
                    live_summary_reconcile_ok = True
                elif val == 'false':
                    live_summary_reconcile_ok = False

    # Go/No-Go data
    go_nogo_summary = ""
    consecutive_pass = 0
    remaining = 3
    if go_nogo_latest.exists():
        with open(go_nogo_latest, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract summary line
            for line in content.split('\n'):
                if line.startswith('Summary:'):
                    go_nogo_summary = line.split(':', 1)[1].strip()
                    break
            # Extract consecutive_pass
            match = re.search(r'consecutive_pass=(\d+)', content)
            if match:
                consecutive_pass = int(match.group(1))
            # Extract remaining
            match = re.search(r'remaining=(\d+)', content)
            if match:
                remaining = int(match.group(1))

    # Conclusion
    conclusion = "NO-GO"
    reason = "insufficient data"
    if consecutive_pass >= 3:
        conclusion = "GO"
        reason = f"READY_TESTNET True ({consecutive_pass}/3, remaining={remaining})"
    else:
        reason = f"consecutive_pass={consecutive_pass}/3, remaining={remaining}"

    kill_switch_text = "有り（有りならlive/paperの危険ステップはSKIP）" if kill_switch else "無し"

    # API configuration warning
    warning_block = ""
    if not api_configured and trader_mode in ('testnet', 'live'):
        required_keys = []
        if trader_mode == 'testnet':
            required_keys = ['BINANCE_TESTNET_API_KEY', 'BINANCE_TESTNET_API_SECRET']
        elif trader_mode == 'live':
            required_keys = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
        warning_block = f"""
WARNING: API_NOT_CONFIGURED
Set .env: {required_keys[0]} / {required_keys[1]} (mode={trader_mode})

⚠️ WARNING: APIキー未設定のため live_trade_run と reconcile_live をスキップしました。

次にやるべきこと:
- .envファイルに以下の環境変数を設定してください:
  * {required_keys[0]}
  * {required_keys[1]}
- 値は空でなく、"dummy" を含まない有効なキーを設定してください。
- 設定後、daily_run を再度実行してください。
"""

    # Template
    template = """# 最小ロットLive Go/No-Goチェックリスト（最終版 / 貼り付け用）

{warning_block}

■ スナップショット

* 実行日時(JST): {now_jst}
* 実行ホスト: {hostname}
* daily_run 最新ログ: {latest_daily_log}
* go_nogo 最新: {go_nogo_latest}
* 状態ファイル/台帳:

  * paper state: {paper_state}
  * live ledger: {live_ledgers}
  * reconcile: {reconcile_latest}

■ 0) 結論（GO / NO-GO）

* 判定: {conclusion}
* 理由（1行）: {reason}

---

■ 1) モード/誤発注防止（最重要）

* TRADER_MODE: {trader_mode}
* TRADER_DRY_RUN: {dry_run}
* KILL_SWITCH: {kill_switch_text}
* LIVEアーミング（confirm一致）:

  * TRADER_LIVE_CONFIRM: {live_confirm}
  * armed 判定: {armed}
  * ルール: armed=True（= mode=live + dry_run=false + confirm一致）以外は「注文禁止（BLOCKED_CONFIRMをledger記録 + alert）」であること

✅ PASS条件:

* 「live + dry_run=false + confirm不一致」で“注文が出ない”こと（BLOCKED_CONFIRMが記録される or そもそも注文フローに入らない）
* ※注意: 今回のように action=None（売買不要）だと confirm ブロックが発火しないことがある。confirmゲートの動作確認は「実際に buy/sell が発生する状況」で再確認する。

---

■ 2) 運用ガード（放置運用の生命線）

* Single instance lock:

  * lock acquired/released がログに出る: {lock_acquired_text}
  * 二重起動時の挙動: 新しい方が安全に exit 0（または一定ルール）: {lock_acquired_text}
* ops_cleanup:

  * [STEP] ops_cleanup と [GUARD] ops_cleanup done が直近24hログに存在: {ops_cleanup_text}
  * ログ/レポート肥大化対策（30日削除・historyローテ等）: {ops_cleanup_text}
* スケジュールタスク:

  * TaskName: ai-agents_daily_run_2300
  * LastTaskResult: {{0 or code}} / LastRunTime: {{time}}
  * 失敗時に通知される（RC_SUMMARY!=0 等）: {{PASS/FAIL}}

---

■ 3) 接続・環境変数（Testnet/Liveの事故ポイント）

* .envロード: load_dotenv が有効（override=False）: {{PASS/FAIL}}
* APIキー参照の一致:

  * Testnet: BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET
  * Live   : BINANCE_API_KEY / BINANCE_API_SECRET
  * check_env_vars.ps1 で Missing/Unused が矛盾なし: {{PASS/FAIL}}
* ccxt 動作: 取引所情報取得・レート制限検知が正常: {{PASS/FAIL}}

---

■ 4) Reconciliation（“一致してないなら取引しない”）

* reconcile_latest.json:

  * exists: {reconcile_exists}
  * ok: {reconcile_ok}
  * 差分（残高/建玉/注文）: {{なし/あり(内容)}}
* run_live_trade の summary:

  * reconcile_ok: {live_summary_reconcile_ok}

✅ PASS条件（最小ロットLive前提）:

* testnet / live で reconcile_ok=true が継続して取れること
* ok=false や None が続くなら NO-GO（原因解消まで）

---

■ 5) 損失ガード（最小ロットLiveのブレーキ）

* 日次最大損失（JPY換算）: {{値}} / 今日の損益: {{値}}
* 最大ポジ（quote notional）: {{値}} / 現在: {{値}}
* 最大ポジ（JPY換算）: {{値}} / 現在: {{値}}
* allow_market: {{false推奨}}（最小ロットLiveはLIMIT ONLYが基本）
* 異常スプレッド停止/連敗停止: {{設定有無}} / 発火履歴: {{有無}}

✅ PASS条件:

* すべてのガードが “踏んだら止まる＆記録される＆通知される” こと
* ブロックされた試行も ledger に残ること

---

■ 6) 注文ID管理・部分約定・台帳（後追いできるか）

* ledger（live_orders_history.csv 等）:

  * client_order_id / order_id / status / filled / remaining / avg_price が記録: {{PASS/FAIL}}
  * BLOCKED_CONFIRM / BLOCKED_RISK も記録: {{PASS/FAIL}}
* リトライと冪等性:

  * 同一 client_order_id の重複発注を防げる: {{PASS/FAIL}}

---

■ 7) Go/No-Go（放置で勝手に整う指標）

* 最新 go_nogo:

  * Summary: {go_nogo_summary}
  * checks: order_management={{PASS/FAIL}}, reconcile={{PASS/FAIL}}, risk_guard={{PASS/FAIL}}, operations={{PASS/FAIL}}

✅ 最小ロットLiveのGO条件（推奨ルール）:

* READY_TESTNET: True (consecutive_pass=3/3) を達成
* Testnetで「DRY_RUN=false + LIMIT ONLY」で少額の発注→約定→reconcile_ok=true を複数回確認
* Liveはまず DRY_RUN=true（シャドー）で reconcile_ok=true を継続
* その後、Live armed=True（confirm一致）＋最小ロットで開始

---

■ 8) 次アクション（1つだけ書く）

* {{例: ①TestnetでDRY_RUN=falseのLIMIT注文を1回だけ通して、部分約定〜reconcileまでの一連ログを確認する／②reconcile_ok が None になる条件を潰す 等}}
"""

    return template.format(
        warning_block=warning_block,
        now_jst=now_jst.strftime("%Y/%m/%d %H:%M"),
        hostname=hostname,
        latest_daily_log=latest_daily_log or "{{scripts\\logs\\daily_run_YYYYMMDD_HHMMSS.log}}",
        go_nogo_latest=go_nogo_latest if go_nogo_latest.exists() else "{{trader\\reports\\go_nogo_latest.txt}}",
        paper_state=paper_state if paper_state.exists() else "{{D:\\ai-data\\paper_state.json}}",
        live_ledgers=", ".join([str(p) for p in live_ledgers]) or "{{trader\\reports\\live_*history*.csv}}",
        reconcile_latest=reconcile_latest if reconcile_latest.exists() else "{{trader\\reports\\reconcile_latest.json}}",
        trader_mode=trader_mode,
        dry_run=dry_run,
        live_confirm=live_confirm or "{{設定値}}",
        armed=armed,
        reconcile_exists=reconcile_exists,
        reconcile_ok=reconcile_ok,
        live_summary_reconcile_ok=live_summary_reconcile_ok,
        go_nogo_summary=go_nogo_summary or "{{READY_PAPER/READY_TESTNET/READY_LIVE}} (consecutive_pass={{n}}/3)",
        conclusion=conclusion,
        reason=reason,
        kill_switch_text=kill_switch_text,
        lock_acquired_text=lock_acquired_text,
        ops_cleanup_text=ops_cleanup_text,
    )