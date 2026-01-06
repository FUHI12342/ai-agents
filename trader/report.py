import json
import os
from pathlib import Path
from datetime import datetime
from .config import LOG_DIR

try:
    import openai
except ImportError:
    openai = None

class SimpleOpenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    def responses_create(self, model, input_text):
        url = f"{self.base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "input": input_text
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return SimpleResponse(result)
        except Exception as e:
            return SimpleResponse({"error": str(e)})

class SimpleResponse:
    def __init__(self, data):
        self.data = data

    @property
    def output_text(self):
        if 'output' in self.data and self.data['output']:
            return self.data['output'][0].get('content', [{}])[0].get('text', {}).get('value', '')
        return ''

def get_client():
    if openai is None:
        return None
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)


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




def generate_multi_trading_report(session: str, summary_input: str, llm_mode: str) -> str:
    """
    複数銘柄のまとめレポートを生成
    llm_mode: "never" (LLMなし), "auto" (APIキーがなければフォールバック), "force" (APIキーが必須)
    """
    client = get_client()

    if llm_mode == "never":
        # LLMなしのテンプレレポート
        return f"""
[トレードレポート - LLMなし]

時間帯: {session}

まとめデータ:
{summary_input}

Profile: preset=good_20_100_risk_0_5, short_window=20, long_window=100, risk_pct=0.5, fee_rate=0.0005

Summary Table:
Symbol | Return | MaxDD | Sharpe | Trades | Final
-------|--------|-------|--------|--------|------
(データなし - LLMなしモード)

各銘柄の詳細: データなし

不明な項目は「不明」と記載。
"""

    elif llm_mode == "auto":
        if client is None:
            # フォールバック
            return f"""
[トレードレポート - LLMなし (APIキーなし)]

時間帯: {session}

まとめデータ:
{summary_input}

Profile: preset=good_20_100_risk_0_5, short_window=20, long_window=100, risk_pct=0.5, fee_rate=0.0005

Summary Table:
Symbol | Return | MaxDD | Sharpe | Trades | Final
-------|--------|-------|--------|--------|------
(データなし - APIキーなし)

各銘柄の詳細: データなし

不明な項目は「不明」と記載。
"""
        else:
            # LLMで生成
            prompt = f"""
あなたは慎重なトレードアドバイザーです。
以下は複数銘柄のバックテスト結果とニュース概要です。

[時間帯]
{session}

[まとめデータ]
{summary_input}

以下を日本語でまとめてください：

Profile: preset=good_20_100_risk_0_5, short_window=20, long_window=100, risk_pct=0.5, fee_rate=0.0005

Summary Table:
Symbol | Return | MaxDD | Sharpe | Trades | Final
-------|--------|-------|--------|--------|------
(各銘柄の行をここに挿入)

各銘柄の詳細セクション（ニュース3件＋注意点）

不明な項目は「不明」と記載してください。
箇条書きベースで、読みやすく簡潔にお願いします。
"""
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = resp.choices[0].message.content
                return text
            except Exception as e:
                return f"レポート生成中にエラーが発生しました: {e}"

    elif llm_mode == "force":
        if client is None:
            raise RuntimeError("OPENAI_API_KEY is required for llm_mode='force'")
        else:
            # LLMで生成
            prompt = f"""
あなたは慎重なトレードアドバイザーです。
以下は複数銘柄のバックテスト結果とニュース概要です。

[時間帯]
{session}

[まとめデータ]
{summary_input}

以下を日本語でまとめてください：

Profile: preset=good_20_100_risk_0_5, short_window=20, long_window=100, risk_pct=0.5, fee_rate=0.0005

Summary Table:
Symbol | Return | MaxDD | Sharpe | Trades | Final
-------|--------|-------|--------|--------|------
(各銘柄の行をここに挿入)

各銘柄の詳細セクション（ニュース3件＋注意点）

不明な項目は「不明」と記載してください。
箇条書きベースで、読みやすく簡潔にお願いします。
"""
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                text = resp.choices[0].message.content
                return text
            except Exception as e:
                return f"レポート生成中にエラーが発生しました: {e}"

    else:
        raise ValueError(f"Invalid llm_mode: {llm_mode}. Must be 'never', 'auto', or 'force'")
