from pathlib import Path

# プロジェクトのパス
BASE_DIR = Path(r"C:\Users\FHiro\Projects\ai-agents\trader")

# データ・ログ・モデルの保存先
DATA_DIR = Path(r"D:\ai-data\trader\data")
LOG_DIR = Path(r"D:\ai-data\trader\logs")
MODELS_DIR = Path(r"D:\ai-data\trader\models")

INITIAL_CAPITAL = 10_000  # 最初の資金（円）
FEE_RATE = 0.0005         # 手数料率の仮値

# フォルダが無ければ作る
for p in [DATA_DIR, LOG_DIR, MODELS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
