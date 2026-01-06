import time
import json
import urllib.request
import urllib.error
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from .config import DATA_DIR, START_DATE

def fetch_binance_klines(symbol: str, interval: str = "1d", start_time: int = None, limit: int = 1000) -> list:
    """
    Binance Klines APIからデータを取得（ページング対応）
    https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
    """
    base_url = "https://api.binance.com/api/v3/klines"
    all_klines = []
    current_start_time = start_time

    while True:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }
        if current_start_time:
            params["startTime"] = current_start_time

        query = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{base_url}?{query}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    break
            except (urllib.error.URLError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    time.sleep(wait_time)
                else:
                    raise e
        else:
            raise Exception("Failed to fetch data after retries")

        if not data:
            break

        all_klines.extend(data)

        # 次のページがあるかチェック（limit分取得できた場合）
        if len(data) < limit:
            break

        # 次のstartTimeを設定（最後のデータのtimestamp + 1ms）
        current_start_time = data[-1][0] + 1

        # 無限ループ防止（現在の時間まで）
        if current_start_time > int(time.time() * 1000):
            break

    return all_klines

def update_data(symbol: str, interval: str = "1d", data_dir: Path = None) -> tuple[str, str, int]:
    """
    Binanceから最新データを取得してCSVを更新
    戻り値: (old_last_date, new_last_date, added_rows)
    """
    if data_dir is None:
        data_dir = DATA_DIR

    # ファイル名を Binance_{symbol}_d.csv に統一（1dの場合）
    if interval == "1d":
        csv_filename = f"Binance_{symbol}_d.csv"
    else:
        csv_filename = f"Binance_{symbol}_{interval}.csv"

    csv_path = data_dir / csv_filename

    # 既存データの最終Unixを取得
    old_last_unix = None
    existing_df = None
    if csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path, skiprows=1, header=0)
            existing_df["Unix"] = existing_df["Unix"].astype(int)
            existing_df = existing_df.sort_values("Unix", ascending=False).reset_index(drop=True)  # Date降順なのでUnix降順
            old_last_unix = existing_df["Unix"].max()
        except Exception:
            pass  # 読み込み失敗時は新規作成扱い

    # 取得開始時間を決定
    start_time = None
    if old_last_unix:
        # 最終Unixの翌日0時から取得
        start_datetime = datetime.fromtimestamp(old_last_unix / 1000) + timedelta(days=1)
        start_time = int(start_datetime.timestamp() * 1000)
    else:
        # 既存がない場合、START_DATEから
        start_datetime = datetime.strptime(START_DATE, "%Y-%m-%d")
        start_time = int(start_datetime.timestamp() * 1000)

    # データ取得（ページング対応）
    klines = fetch_binance_klines(symbol, interval, start_time)

    if not klines:
        old_last_date = datetime.fromtimestamp(old_last_unix / 1000).strftime("%Y-%m-%d") if old_last_unix else "None"
        return (old_last_date, "None", 0)

    # DataFrame変換
    new_df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    new_df["Unix"] = new_df["timestamp"].astype(int)
    new_df["Date"] = pd.to_datetime(new_df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
    new_df["Symbol"] = symbol.upper()
    new_df["Open"] = new_df["open"].astype(float)
    new_df["High"] = new_df["high"].astype(float)
    new_df["Low"] = new_df["low"].astype(float)
    new_df["Close"] = new_df["close"].astype(float)
    new_df["Volume BTC"] = new_df["volume"].astype(float)
    new_df["Volume USDT"] = new_df["quote_asset_volume"].astype(float)
    new_df["tradecount"] = new_df["number_of_trades"].astype(int)

    new_df = new_df[["Unix", "Date", "Symbol", "Open", "High", "Low", "Close", "Volume BTC", "Volume USDT", "tradecount"]]

    # 既存データと結合
    if existing_df is not None:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset="Unix", keep="last")
        combined_df = combined_df.sort_values("Unix", ascending=False).reset_index(drop=True)  # Date降順
    else:
        combined_df = new_df.sort_values("Unix", ascending=False).reset_index(drop=True)

    # CSV書き出し（1行目はCryptoDataDownload URL）
    crypto_url = "https://www.CryptoDataDownload.com"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "w", newline="") as f:
        f.write(f"{crypto_url}\n")
        combined_df.to_csv(f, index=False)

    new_last_unix = combined_df["Unix"].max()
    new_last_date = datetime.fromtimestamp(new_last_unix / 1000).strftime("%Y-%m-%d")
    old_last_date = datetime.fromtimestamp(old_last_unix / 1000).strftime("%Y-%m-%d") if old_last_unix else "None"
    added_rows = len(new_df)

    return (old_last_date, new_last_date, added_rows)

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Update Binance OHLCV data")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--interval", default="1d", help="Interval (default: 1d)")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="Data directory")

    args = parser.parse_args()

    try:
        old_last, new_last, added = update_data(args.symbol, args.interval, args.data_dir)
        print(f"Updated {args.symbol} {args.interval}: old_last={old_last} new_last={new_last} added_rows={added}")
        return 0
    except Exception as e:
        print(f"Error updating data: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())