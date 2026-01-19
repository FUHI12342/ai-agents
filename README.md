# ai-agents

## Compack (voice/text agent)

- Docs: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) / [docs/DATA_FLOW.md](docs/DATA_FLOW.md) / [docs/ROADMAP.md](docs/ROADMAP.md)
- Quick start (text mode, new session): `python -m apps.compack.main --mode text --resume new`
- Diagnostics (includes GPU estimate via ollama ps / nvidia-smi): `python -m apps.compack.main --diagnose --mode text`
- Desktop shortcuts (Windows): `powershell -ExecutionPolicy Bypass -File scripts/create_shortcuts.ps1`
- Verify git/worktree state: `powershell -ExecutionPolicy Bypass -File scripts/git_verify.ps1`

## Trader Module

### 単体運用例

```bash
# プリセット一覧
python -m trader.run_backtest_with_risk --list-presets

# 単体バックテスト
python -m trader.run_backtest_with_risk --preset good_20_100_risk_0_5 --symbol BTCUSDT

# 単体レポート生成
python -m trader.daily_report morning --preset good_20_100_risk_0_5
```

### 複数銘柄まとめ運用例

```bash
# 複数銘柄レポート生成（1回LLM呼び出し）
python -m trader.daily_report morning --preset good_20_100_risk_0_5 --symbols BTCUSDT,ETHUSDT --force

# LLMモード指定例
# 初回は force で要約生成
python -m trader.daily_report morning --preset good_20_100_risk_0_5 --symbols BTCUSDT,ETHUSDT --llm-mode force
# 平常運用は auto（差分小ならSKIP）
python -m trader.daily_report morning --preset good_20_100_risk_0_5 --symbols BTCUSDT,ETHUSDT --llm-mode auto
# 節約テストは never（常にSKIP）
python -m trader.daily_report morning --preset good_20_100_risk_0_5 --symbols BTCUSDT,ETHUSDT --llm-mode never

# run_session.ps1 での実行例（手動、DryRunで送信スキップ）
.\scripts\run_session.ps1 -Session morning -ToAddr "test@example.com" -Preset good_20_100_risk_0_5 -Symbols "BTCUSDT,ETHUSDT" -UpdateData -DryRun

# LLMモード指定例（run_session.ps1）
.\scripts\run_session.ps1 -Session morning -ToAddr "test@example.com" -Preset good_20_100_risk_0_5 -Symbols "BTCUSDT,ETHUSDT" -LlmMode auto -UpdateData -DryRun

# 送信あり（DryRunなし）
.\scripts\run_session.ps1 -Session morning -ToAddr "test@example.com" -Preset good_20_100_risk_0_5 -Symbols "BTCUSDT,ETHUSDT" -LlmMode auto -UpdateData

# タスクスケジューラでの実行例（/TR に渡すコマンド）
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\FHiro\Projects\ai-agents\scripts\run_session.ps1" -Session morning -ToAddr "test@example.com" -Preset good_20_100_risk_0_5 -Symbols "BTCUSDT,ETHUSDT" -UpdateData

### タスクスケジューラ設定（GUI）
1. タスクスケジューラを開く
2. 「タスクの作成」を選択
3. 全般タブ:
   - 名前: TraderMorning
   - 「最上位の特権で実行する」をチェック
   - 「ユーザーがログオンしているかどうかにかかわらず実行する」をチェック
4. トリガー: 毎日 07:30
5. アクション: プログラムの開始
   - プログラム: powershell.exe
   - 引数: -NoProfile -ExecutionPolicy Bypass -File "C:\Users\FHiro\Projects\ai-agents\scripts\run_session.ps1" -Session morning -ToAddr "takeshiminaminoshima1@gmail.com" -Symbols BTCUSDT,ETHUSDT -Preset good_20_100_risk_0_5 -UpdateData -LlmMode auto
   - 開始: C:\Users\FHiro\Projects\ai-agents
6. 条件タブ: 「コンピューターがAC電源で使用されている場合のみタスクを開始する」のチェックを外す

### タスクスケジューラ設定（コマンド）
.\scripts\setup_trader_task.ps1 -TaskName TraderMorning -StartTime 07:30 -Session morning -ToAddr takeshiminaminoshima1@gmail.com -Symbols BTCUSDT,ETHUSDT -Preset good_20_100_risk_0_5 -UpdateData -LlmMode auto -RunAsPassword (パスワード)
```

### Live Trading (Experimental)

#### 概要
- デフォルトは **Paper Mode**（絶対に実注文なし）
- Live/Testnet 実行は明示設定 + 確認文言必須
- リスクガード：損失制限、スプレッドチェック、連敗停止等

#### 設定
1. `.env` ファイル作成（.env.example をコピー）
2. 環境変数設定:
   ```
   TRADER_MODE=paper  # paper|testnet|live
   TRADER_CCXT_EXCHANGE=binance
   TRADER_CCXT_API_KEY=your_api_key
   TRADER_CCXT_API_SECRET=your_api_secret
   TRADER_CCXT_SANDBOX=1  # 1 for testnet
   TRADER_LIVE_CONFIRM=I_UNDERSTAND_LIVE_TRADING_RISK  # Must match exactly for live/testnet
   TRADER_TRADER_SYMBOLS=BTC/USDT
   TRADER_MAX_DAILY_LOSS_JPY=1000
   TRADER_MAX_POSITION_NOTIONAL_JPY=5000
   TRADER_MAX_SPREAD_BPS=30
   ```
3. APIキー取得（Binance等）
4. Testnetでテスト（TRADER_MODE=testnet, TRADER_CCXT_SANDBOX=1）

#### 実行
- 単体実行: `python -m trader.run_live_trade`
- Daily Run: `.\scripts\daily_run.ps1 -NoMail`
- 毎日23:00自動実行（設定済み）

#### 安全機能
- KILL_SWITCH ファイル存在で全取引SKIP
- Paper Mode では常にSKIP
- Confirm 文言不一致でエラー終了
- リスク超過で注文キャンセル

#### 監視
- Ledger: trader/reports/live_orders_history.csv 等
- Reconcile: trader/reports/reconcile_latest.txt
- Summary: trader/reports/live_summary_latest.txt

### Yahoo Daily Paper Simulation

#### 実行
```bash
# Yahoo日足Paper Simulation
python -m trader.run_paper_sim_yahoo --symbols ^N225,USDJPY=X --capital-jpy 10000 --ma-short 20 --ma-long 100 --risk-pct 0.25 --state-file D:\ai-data\paper_state_yahoo.json --out-dir trader\reports

# 結果確認
Get-Content trader\reports\paper_yahoo_summary_latest.txt -Tail 200
```

#### ロールアウト手順
1. Paper Mode 確認（デフォルト）
2. .env 作成、Testnet設定
3. TRADER_MODE=testnet, TRADER_LIVE_CONFIRM=I_UNDERSTAND_LIVE_TRADING_RISK
4. 単体実行テスト
5. Daily Run -NoMail テスト
6. 本番メール監視開始
7. Live移行（TRADER_MODE=live, TRADER_CCXT_SANDBOX=0）

### 環境変数

- `TRADER_SYMBOL`: デフォルト銘柄（例: BTCUSDT）
- `TRADER_SYMBOLS`: カンマ区切り複数銘柄（例: BTCUSDT,ETHUSDT）- CLI --symbols より優先度低い
- Live関連: 上記Live Trading セクション参照
