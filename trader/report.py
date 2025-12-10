import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from .config import LOG_DIR

# .env から OPENAI_API_KEY を読み込む
load_dotenv()
client = OpenAI()


def load_today_backtest_log() -> str:
    """今日のバックテストログをまとめてテキスト化"""
    date_str = datetime.now().strftime("%Y%m%d")
    path = LOG_DIR / f"backtest_{date_str}.log"
    if not path.exists():
        return "本日のバックテストログはまだありません。"

    lines = path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    text_lines = []
    for r in records:
        text_lines.append(
            f"{r['timestamp']} symbol={r['symbol']} pnl={r['pnl']:.2f} final_equity={r['final_equity']:.2f}"
        )
    return "\n".join(text_lines) if text_lines else "ログはありますが、中身が空です。"


def _extract_text_from_response(resp) -> str:
    """
    OpenAI Responses API のレスポンスからテキストを安全に取り出すヘルパー。

    - resp.output_text があればそれを優先
    - なければ resp.output[*].content[*].text.value を総なめ
    - それでも無ければエラーメッセージを返す
    """
    # まずは便利プロパティ output_text を試す
    if getattr(resp, "output_text", None):
        return resp.output_text

    parts = []

    output = getattr(resp, "output", None)
    if not output:
        return "(モデルからのテキスト出力がありませんでした)"

    for item in output:
        contents = getattr(item, "content", None)
        if not contents:
            continue

        for c in contents:
            # OpenAI Python SDK の text オブジェクトを想定
            txt = getattr(c, "text", None)
            if not txt:
                continue

            # text.value を優先
            value = getattr(txt, "value", None)
            if value:
                parts.append(value)
            else:
                # 念のため str() で文字列化
                parts.append(str(txt))

    return "\n".join(parts) if parts else "(モデルからのテキスト出力がありませんでした)"


def generate_trading_report(session: str, news_text: str) -> str:
    """
    session: 'morning' / 'noon' / 'night' など
    news_text: その時間帯のニュース要約テキスト（最初は手動でもOK）
    """
    log_text = load_today_backtest_log()

    prompt = f"""
あなたは慎重なトレードアドバイザーです。
以下は今日のバックテスト結果とニュース概要です。

[時間帯]
{session}

[バックテストログ]
{log_text}

[ニュース]
{news_text}

以下を日本語でまとめてください：

1. 現在の戦略の状態とリスクの簡単な診断
2. この時間帯に注意すべきポイント（やってはいけない行動を中心に）
3. 次の時間帯までに確認しておくと良い指標やイベント

箇条書きベースで、読みやすく簡潔にお願いします。
"""

    try:
        resp = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )
        text = _extract_text_from_response(resp)
        return text
    except Exception as e:
        # ここで例外内容も一応返しておくとデバッグしやすい
        return f"レポート生成中にエラーが発生しました: {e}"
