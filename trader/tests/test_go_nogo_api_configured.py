import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

from trader.go_nogo import check_go_nogo


class TestGoNoGoAPIConfigured:
    @patch('trader.go_nogo.load_config')
    @patch('trader.go_nogo.load_history', return_value=[])
    @patch('trader.go_nogo.BASE_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_api_not_configured_testnet(self, mock_base_dir, mock_load_history, mock_load_config):
        mock_config = MagicMock()
        mock_config.trader_mode = 'testnet'
        mock_config.is_api_configured.return_value = False
        mock_load_config.return_value = mock_config

        results = check_go_nogo()

        assert results['ready'] is False
        assert 'api_not_configured' in results['summary']
        assert results['checks']['api_configured'] is False

    @patch('trader.go_nogo.load_config')
    @patch('trader.go_nogo.load_history', return_value=[])
    @patch('trader.go_nogo.BASE_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_api_configured_testnet(self, mock_base_dir, mock_load_history, mock_load_config):
        mock_config = MagicMock()
        mock_config.trader_mode = 'testnet'
        mock_config.is_api_configured.return_value = True
        mock_load_config.return_value = mock_config

        results = check_go_nogo()

        assert results['checks']['api_configured'] is True

    @patch('trader.go_nogo.load_config')
    @patch('trader.go_nogo.load_history', return_value=[])
    @patch('trader.go_nogo.BASE_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_paper_yahoo_candles_zero_fail(self, mock_base_dir, mock_load_history, mock_load_config):
        mock_config = MagicMock()
        mock_config.trader_mode = 'paper'
        mock_config.is_api_configured.return_value = True
        mock_load_config.return_value = mock_config

        reports_dir = mock_base_dir / "reports"
        reports_dir.mkdir()
        summary_file = reports_dir / "paper_yahoo_summary_latest.txt"
        # Simulate summary with candles=0
        summary_file.write_text("""
Yahoo PaperTrade Simulation (MA cross) 2023/01/01 12:00:00
JPY/USDT assumed: 150.0000

[^N225] candles=0 last=(none) reason=NO_DATA
- equity_jpy: 10000.00  return: 0.00%  maxDD: 0.00%
- cash_quote: 66.6667  pos_base: 0.0000  new_trades: 0

Files
- latest trades : trader/reports/paper_yahoo_trades_latest.csv
- history trades: trader/reports/paper_yahoo_trades_history.csv
- state         : D:\ai-data\paper_state_yahoo.json
""")

        results = check_go_nogo()

        assert results['checks']['paper_yahoo'] is False

    @patch('trader.go_nogo.load_config')
    @patch('trader.go_nogo.load_history', return_value=[])
    @patch('trader.go_nogo.BASE_DIR', new_callable=lambda: Path(tempfile.mkdtemp()))
    def test_paper_yahoo_valid_pass(self, mock_base_dir, mock_load_history, mock_load_config):
        mock_config = MagicMock()
        mock_config.trader_mode = 'paper'
        mock_config.is_api_configured.return_value = True
        mock_load_config.return_value = mock_config

        reports_dir = mock_base_dir / "reports"
        reports_dir.mkdir()
        summary_file = reports_dir / "paper_yahoo_summary_latest.txt"
        # Simulate valid summary
        summary_file.write_text("""
Yahoo PaperTrade Simulation (MA cross) 2023/01/01 12:00:00
JPY/USDT assumed: 150.0000

[^N225] candles=100 last=2023-01-01 12:00:00 UTC reason=OK
- equity_jpy: 10000.00  return: 0.00%  maxDD: 0.00%
- cash_quote: 66.6667  pos_base: 0.0000  new_trades: 0

Files
- latest trades : trader/reports/paper_yahoo_trades_latest.csv
- history trades: trader/reports/paper_yahoo_trades_history.csv
- state         : D:\ai-data\paper_state_yahoo.json
""")

        results = check_go_nogo()

        assert results['checks']['paper_yahoo'] is True