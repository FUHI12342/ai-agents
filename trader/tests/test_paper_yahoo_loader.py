import tempfile
import pandas as pd
from pathlib import Path
import pytest

from trader.paper_engine_yahoo import load_yahoo_ohlcv
from trader.yahoo_symbols import symbol_to_yahoo_file_stem


def test_load_yahoo_ohlcv():
    # Create sample CSV content (Yahoo Finance format)
    csv_content = """date,open,high,low,close,adj_close,volume
2023-01-01,100.0,105.0,95.0,102.0,102.0,1000
2023-01-02,102.0,108.0,98.0,105.0,105.0,1100
2023-01-03,105.0,110.0,100.0,108.0,108.0,1200
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        csv_path = data_dir / "Yahoo_test_d.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        ohlcv = load_yahoo_ohlcv("test", data_dir)

        assert len(ohlcv) == 3
        # Check first row
        ts, o, h, l, c, v = ohlcv[0]
        assert o == 100.0
        assert h == 105.0
        assert l == 95.0
        assert c == 102.0
        assert v == 1000.0
        # ts_ms is timestamp
        assert isinstance(ts, int)
        assert ts > 0

        # Check sorted by date
        assert ohlcv[0][0] < ohlcv[1][0] < ohlcv[2][0]


def test_load_yahoo_ohlcv_two_header():
    # Create sample CSV content with 2-header format (second row has symbol info)
    csv_content = """date,open,high,low,close,adj_close,volume
,^N225,^N225,^N225,^N225,^N225,^N225
2023-01-01,100.0,105.0,95.0,102.0,102.0,1000
2023-01-02,102.0,108.0,98.0,105.0,105.0,1100
2023-01-03,105.0,110.0,100.0,108.0,108.0,1200
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        csv_path = data_dir / "Yahoo_test_d.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        ohlcv = load_yahoo_ohlcv("test", data_dir)

        assert len(ohlcv) == 3
        # Check first row
        ts, o, h, l, c, v = ohlcv[0]
        assert o == 100.0
        assert h == 105.0
        assert l == 95.0
        assert c == 102.0
        assert v == 1000.0
        # ts_ms is timestamp
        assert isinstance(ts, int)
        assert ts > 0

        # Check sorted by date
        assert ohlcv[0][0] < ohlcv[1][0] < ohlcv[2][0]


def test_load_yahoo_ohlcv_file_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        with pytest.raises(FileNotFoundError):
            load_yahoo_ohlcv("nonexistent", data_dir)


def test_yahoo_symbol_to_file_stem():
    assert symbol_to_yahoo_file_stem("^N225") == "N225"
    assert symbol_to_yahoo_file_stem("^GSPC") == "GSPC"
    assert symbol_to_yahoo_file_stem("USDJPY=X") == "USDJPY_X"
    assert symbol_to_yahoo_file_stem("BTC-USD") == "BTC-USD"


def test_load_yahoo_ohlcv_empty_after_processing():
    # CSV with invalid numeric values that become NaN and get dropped
    csv_content = """date,open,high,low,close,adj_close,volume
2023-01-01,abc,105.0,95.0,102.0,102.0,1000
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        csv_path = data_dir / "Yahoo_test_d.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        with pytest.raises(ValueError, match="Loaded DataFrame is empty after processing"):
            load_yahoo_ohlcv("test", data_dir)