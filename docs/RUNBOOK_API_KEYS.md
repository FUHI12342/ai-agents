# APIキー発行手順

このドキュメントでは、Binance APIキーの発行手順を説明します。テストネットとライブ取引に対応しています。

## テストネット (Testnet)

### Spot Testnet
1. [testnet.binance.vision](https://testnet.binance.vision) にアクセス
2. GitHubアカウントでログイン
3. "Generate HMAC_SHA256 Key" をクリック
4. API Key と Secret が表示される（再表示されないのでメモ）
5. .env ファイルに以下を設定:
   ```
   BINANCE_TESTNET_API_KEY=your_api_key_here
   BINANCE_TESTNET_API_SECRET=your_secret_here
   ```

### Futures Demo (Testnet)
1. [demo.binance.com](https://demo.binance.com) にアクセス
2. API Management をクリック
3. Create API をクリック
4. API Key と Secret が生成される
5. .env ファイルに以下を設定:
   ```
   BINANCE_TESTNET_API_KEY=your_api_key_here
   BINANCE_TESTNET_API_SECRET=your_secret_here
   ```

## ライブ取引 (Live)

### Binance 本番アカウント
1. [Binance](https://www.binance.com) にログイン
2. プロフィール > API Management をクリック
3. Create API をクリック
4. API Key と Secret が生成される
5. .env ファイルに以下を設定:
   ```
   BINANCE_API_KEY=your_api_key_here
   BINANCE_API_SECRET=your_secret_here
   ```

## セキュリティ注意事項
- IP制限を設定して、許可されたIPのみアクセス可能に
- 権限は最小限に設定（取引権限のみ、資産引き出し権限OFF）
- APIキーとシークレットはリポジトリにコミットしない
- .env ファイルは .gitignore に追加済み

## 参考URL
- [How to create API keys on Binance](https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072)
- [Binance API Documentation](https://www.binance.com/en/support/faq/ab78f9a1b8824cf0a106b4229c76496d)