import os
from dotenv import load_dotenv
from openai import OpenAI

# .env から OPENAI_API_KEY を読み込む
load_dotenv()
client = OpenAI()  # 環境変数から自動でAPIキーを読む

def main():
    resp = client.responses.create(
    model="gpt-5.1",
    input="ローカル環境からAPIへのテストです。1行だけ返事して。"
    )

    # 最初のテキスト出力を取り出す
    text = resp.output[0].content[0].text
    print("=== OpenAI 応答 ===")
    print(text)

if __name__ == "__main__":
    main()