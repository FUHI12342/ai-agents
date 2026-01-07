import unittest
import os
from unittest.mock import patch
from trader.exchange_auth_smoke import main


class TestExchangeAuthSmokeSkip(unittest.TestCase):
    def test_skip_when_api_not_configured(self):
        """Test that auth_smoke skips when API is not configured (dummy keys)"""
        with patch.dict(os.environ, {
            'TRADER_MODE': 'testnet',
            'BINANCE_TESTNET_API_KEY': 'dummy_testnet_key',
            'BINANCE_TESTNET_API_SECRET': 'dummy_testnet_secret'
        }):
            result = main()
            self.assertEqual(result, 0)  # Should return 0 for skip

    def test_skip_when_paper_mode(self):
        """Test that auth_smoke skips in paper mode"""
        with patch.dict(os.environ, {
            'TRADER_MODE': 'paper'
        }):
            result = main()
            self.assertEqual(result, 0)  # Should return 0 for skip


if __name__ == "__main__":
    unittest.main()