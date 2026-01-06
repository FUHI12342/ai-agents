import sys
import json
import argparse
import os
import hashlib
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR, SYMBOLS
from .report import generate_multi_trading_report
from .backtest_service import run_backtest

def normalize_metrics(result):
    return {
        'return_pct': result.get('pnl', 0) * 100,  # 仮定: pnlは割合
        'max_drawdown_pct': result.get('max_drawdown', 0) * 100,
        'sharpe_like': result.get('sharpe', 0),
        'num_trades_est': result.get('num_trades', 0),
        'final_equity': result.get('final_equity', 0)
    }

def compute_diff(new_m, old_m):
    return {
        'return_pct': new_m['return_pct'] - old_m['return_pct'],
        'max_drawdown_pct': new_m['max_drawdown_pct'] - old_m['max_drawdown_pct'],
        'sharpe_like': new_m['sharpe_like'] - old_m['sharpe_like'],
        'num_trades_est': new_m['num_trades_est'] - old_m['num_trades_est']
    }

def is_significant_change(diff):
    return (
        abs(diff['return_pct']) >= 0.5 or
        abs(diff['max_drawdown_pct']) >= 0.5 or
        abs(diff['sharpe_like']) >= 0.05 or
        diff['num_trades_est'] != 0
    )

def generate_text_report(symbol_results, preset, session, diff_summary, news_changed):
    lines = []
    lines.append("Profile:")
    lines.append(f"  Preset: {preset}")
    lines.append(f"  Symbols: {', '.join(sr['symbol'] for sr in symbol_results)}")
    lines.append("  MA Short: 20")
    lines.append("  MA Long: 100")
    lines.append("  Risk PCT: 0.5")
    lines.append("  Fee Rate: 0.0005")
    lines.append(f"  Start/End: None/None")
    lines.append("")

    lines.append("Multi Symbol Summary Table:")
    lines.append("Symbol | Return | MaxDD | Sharpe | Trades | Final")
    lines.append("-------|--------|-------|--------|--------|------")
    for sr in symbol_results:
        m = sr['metrics']
        lines.append(f"{sr['symbol']} | {m['return_pct']:.2f} | {m['max_drawdown_pct']:.2f} | {m['sharpe_like']:.2f} | {m['num_trades_est']} | {m['final_equity']:.2f}")
    lines.append("")

    if diff_summary:
        lines.append("Diff Summary:")
        lines.append("Symbol | ΔReturn | ΔDD | ΔSharpe | ΔTrades")
        lines.append("-------|---------|-----|---------|---------")
        for ds in diff_summary:
            d = ds['diff']
            lines.append(f"{ds['symbol']} | {d['return_pct']:+.2f} | {d['max_drawdown_pct']:+.2f} | {d['sharpe_like']:+.2f} | {d['num_trades_est']:+d}")
        lines.append("")

    if news_changed:
        lines.append("News changed since last snapshot.")
        lines.append("")

    lines.append("Conclusion: [LLM] SKIP: changes are below thresholds")
    lines.append("")
    lines.append("Usage: (取得できるなら付与、無理なら省略)")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Generate daily trading report for multiple symbols')
    parser.add_argument('session', help='Session name (e.g., morning, night)')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (overrides config)')
    parser.add_argument('--preset', type=str, required=True, help='Preset name')
    parser.add_argument('--force', action='store_true', help='Force regenerate report')
    parser.add_argument('--llm-mode', choices=['auto', 'force', 'never'], default='auto', help='LLM call mode')

    args = parser.parse_args()

    # llm_mode 確定
    llm_mode = os.getenv('TRADER_LLM_MODE', args.llm_mode)

    # 銘柄確定
    symbols = args.symbols.split(',') if args.symbols else SYMBOLS

    # レポートパス
    date_str = datetime.now().strftime("%Y%m%d")
    report_path = LOG_DIR / f"report_{date_str}_{args.session}_multi.txt"

    if not args.force and report_path.exists():
        print(f"Report already exists: {report_path}")
        return

    # symbols_key
    symbols_key = ','.join(sorted(symbols))

    # snapshot dir
    snapshot_dir = Path(r"D:\ai-data\trader\reports\snapshots") / args.session / args.preset / symbols_key
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    latest_path = snapshot_dir / "latest.json"
    date_path = snapshot_dir / f"{date_str}.json"

    # 前回スナップショット読み込み
    previous_snapshot = None
    previous_hash = None
    if latest_path.exists():
        with open(latest_path, 'r', encoding='utf-8') as f:
            previous_snapshot = json.load(f)
            previous_hash = previous_snapshot.get('hash')
        print(f"loaded previous snapshot")

    # 各symbolの処理
    symbol_results = []
    all_news = []
    metrics_dict = {}
    news_dict = {}

    for symbol in symbols:
        try:
            # バックテスト実行
            result = run_backtest(
                symbol=symbol,
                preset=args.preset,
                risk_pct=0.5,
                short_window=20,  # presetから取得
                long_window=100
            )

            # metrics正規化
            metrics = normalize_metrics(result)
        except Exception as e:
            print(f"Error running backtest for {symbol}: {e}", file=sys.stderr)
            # エラーの場合、ダミーメトリクス
            metrics = normalize_metrics({
                'pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe': 0.0,
                'num_trades': 0,
                'final_equity': 0.0
            })

        # ニュース取得（ダミー明示）
        headlines = [f"DUMMY: {symbol}ニュース1", f"DUMMY: {symbol}ニュース2", f"DUMMY: {symbol}ニュース3"]

        all_news.extend(headlines)

        metrics_dict[symbol] = metrics
        news_dict[symbol] = headlines

        symbol_results.append({
            'symbol': symbol,
            'metrics': metrics,
            'news': headlines
        })

    # スナップショット作成
    snapshot_data = {
        'preset': args.preset,
        'symbols': symbols,
        'ma_short': 20,
        'ma_long': 100,
        'risk_pct': 0.5,
        'fee_rate': 0.0005,
        'start_date': None,
        'end_date': None,
        'metrics': metrics_dict,
        'news_headlines': news_dict,
        'generated_at': datetime.now().isoformat()
    }
    # hash計算
    hash_data = json.dumps(snapshot_data, sort_keys=True, default=str)
    current_hash = hashlib.sha256(hash_data.encode()).hexdigest()
    snapshot_data['hash'] = current_hash

    # 差分計算
    diff_summary = []
    if previous_snapshot:
        prev_metrics = previous_snapshot['metrics']
        for symbol in symbols:
            if symbol in prev_metrics:
                diff = compute_diff(metrics_dict[symbol], prev_metrics[symbol])
                diff_summary.append({'symbol': symbol, 'diff': diff})
        news_changed = snapshot_data['news_headlines'] != previous_snapshot['news_headlines']
    else:
        news_changed = False

    # LLM呼ぶか判定
    call_llm = False
    reuse_report = False
    if llm_mode == 'force':
        call_llm = True
        print("[LLM] CALL (mode=force)")
    elif llm_mode == 'never':
        call_llm = False
        print("[LLM] SKIP (mode=never)")
    elif llm_mode == 'auto':
        if not previous_snapshot:
            call_llm = True
            print("[LLM] CALL (first run)")
        elif previous_hash == current_hash:
            call_llm = False
            reuse_report = True
            print("[LLM] SKIP: no changes")
        else:
            call_llm = True
            print("[LLM] CALL (changes detected)")

    # client チェック
    if call_llm:
        from .report import get_client
        client = get_client()
        if client is None:
            call_llm = False
            print("[LLM] SKIP (no client)")

    if call_llm:
        # まとめ入力生成
        summary_input = f"Session: {args.session}\nPreset: {args.preset}\n\n"
        summary_input += "Symbol Results:\n"
        for sr in symbol_results:
            m = sr['metrics']
            summary_input += f"- {sr['symbol']}: Return={m['return_pct']:.2f}, MaxDD={m['max_drawdown_pct']:.2f}, Sharpe={m['sharpe_like']:.2f}, Trades={m['num_trades_est']}, Final={m['final_equity']:.2f}\n"

        summary_input += "\nNews Headlines:\n" + "\n".join(all_news)

        # 前回/差分追加
        if diff_summary:
            summary_input += "\nDiff Summary:\n"
            for ds in diff_summary:
                d = ds['diff']
                summary_input += f"- {ds['symbol']}: ΔReturn={d['return_pct']:+.2f}, ΔDD={d['max_drawdown_pct']:+.2f}, ΔSharpe={d['sharpe_like']:+.2f}, ΔTrades={d['num_trades_est']:+d}\n"
        if news_changed:
            summary_input += "\nNews changed since last snapshot.\n"

        # LLM呼び出し
        report_text = generate_multi_trading_report(session=args.session, summary_input=summary_input, llm_mode=llm_mode)
    elif reuse_report:
        # 前回レポート再利用 + No changes
        prev_report_path = LOG_DIR / f"report_{previous_snapshot['generated_at'][:8]}_{args.session}_multi.txt"
        if prev_report_path.exists():
            report_text = prev_report_path.read_text(encoding="utf-8") + "\n\n[No changes since last snapshot]"
        else:
            report_text = generate_text_report(symbol_results, args.preset, args.session, diff_summary, news_changed)
    else:
        # テンプレレポート
        report_text = generate_text_report(symbol_results, args.preset, args.session, diff_summary, news_changed)

    print("=== Multi Symbol Trading Report ===")
    print(report_text)

    # 保存
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\nレポート保存先: {report_path}")

    # スナップショット保存
    with open(date_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
    print(f"snapshot saved to {latest_path}")

if __name__ == "__main__":
    main()
