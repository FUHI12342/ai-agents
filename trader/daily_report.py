import sys
from datetime import datetime
from pathlib import Path
from .config import LOG_DIR
from .report import generate_trading_report

def main():
    # コマンドライン引数で時間帯指定（デフォルトは "night"）
    session = sys.argv[1] if len(sys.argv) > 1 else "night"

    # ひとまずニュースは仮置きで手動入力 or 固定文字列
    # 後でここに実際のニュース要約を差し込む
    news_text = "今日はテスト運用中。実際のマーケットニュースの代わりに固定テキストを使用。"

    report_text = generate_trading_report(session=session, news_text=news_text)

    print("=== Trading Report ===")
    print(report_text)

    # レポートをファイルにも保存
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = LOG_DIR / f"report_{date_str}_{session}.txt"
    out_path.write_text(report_text, encoding="utf-8")
    print(f"\nレポート保存先: {out_path}")

if __name__ == "__main__":
    main()
