import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestPaperExecutionReport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = os.path.join(self.temp_dir, "paper_state.json")
        self.out_dir = Path(self.temp_dir) / "reports"
        self.out_dir.mkdir()

        # Mock state file
        state_data = {
            "version": 1,
            "created_at": "2023-01-01T00:00:00",
            "initial_capital_jpy": 10000,
            "jpy_per_usdt": 150.0,
            "symbols": {
                "BTCUSDT": {
                    "cash_quote": 5000.0,
                    "pos_base": 0.1,
                    "last_ts": None,
                    "prev_diff": None,
                    "peak_equity_quote": None,
                    "max_drawdown_pct": 0.0,
                    "trades_total": 5
                }
            }
        }
        with open(self.state_file, "w") as f:
            json.dump(state_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('trader.paper_execution_report.ccxt')
    def test_report_generation(self, mock_ccxt):
        """Test that report is generated with required keys"""
        # Mock ccxt binance
        mock_exchange = MagicMock()
        mock_ccxt.binance.return_value = mock_exchange

        # Mock OHLCV data (dummy)
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 47000.0, 48000.0, 46000.0, 47500.0, 1000.0],  # 1h ago
            [1640998800000, 47500.0, 48500.0, 47000.0, 48000.0, 1100.0],  # current
        ]

        # Mock config
        with patch('trader.config.load_config') as mock_load_config:
            mock_config = MagicMock()
            mock_config.trader_mode = 'testnet'
            mock_load_config.return_value = mock_config

            # Import and run
            from trader.paper_execution_report import main

            # Set args
            import sys
            sys.argv = [
                'paper_execution_report.py',
                '--state-file', self.state_file,
                '--symbols', 'BTCUSDT',
                '--ma-short', '20',
                '--ma-long', '100',
                '--risk-pct', '0.25',
                '--jpy-per-usdt', '150',
                '--out-dir', str(self.out_dir)
            ]

            result = main()
            self.assertEqual(result, 0)

            # Check output file
            output_file = self.out_dir / "paper_exec_summary_latest.txt"
            self.assertTrue(output_file.exists())

            content = output_file.read_text()
            self.assertIn("Paper Execution Summary", content)
            self.assertIn("last_signal:", content)
            self.assertIn("next_action:", content)
            self.assertIn("equity_jpy:", content)


if __name__ == "__main__":
    unittest.main()