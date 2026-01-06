import os
import pytest
from unittest.mock import patch
from trader.config import TraderConfig


class TestAPIConfigured:
    @patch.dict(os.environ, {}, clear=True)
    def test_paper_mode_always_true(self):
        config = TraderConfig(trader_mode='paper')
        assert config.is_api_configured() is True

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': 'valid_key',
        'BINANCE_TESTNET_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_testnet_valid_keys(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is True

    @patch.dict(os.environ, {
        'BINANCE_API_KEY': 'valid_key',
        'BINANCE_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_live_valid_keys(self):
        config = TraderConfig(trader_mode='live')
        assert config.is_api_configured() is True

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': '',
        'BINANCE_TESTNET_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_testnet_empty_key(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': 'valid_key',
        'BINANCE_TESTNET_API_SECRET': ''
    }, clear=True)
    def test_testnet_empty_secret(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_API_KEY': '',
        'BINANCE_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_live_empty_key(self):
        config = TraderConfig(trader_mode='live')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_API_KEY': 'valid_key',
        'BINANCE_API_SECRET': ''
    }, clear=True)
    def test_live_empty_secret(self):
        config = TraderConfig(trader_mode='live')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': 'dummy_key',
        'BINANCE_TESTNET_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_testnet_dummy_key(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': 'valid_key',
        'BINANCE_TESTNET_API_SECRET': 'dummy_secret'
    }, clear=True)
    def test_testnet_dummy_secret(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_API_KEY': 'dummy_key',
        'BINANCE_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_live_dummy_key(self):
        config = TraderConfig(trader_mode='live')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_API_KEY': 'valid_key',
        'BINANCE_API_SECRET': 'dummy_secret'
    }, clear=True)
    def test_live_dummy_secret(self):
        config = TraderConfig(trader_mode='live')
        assert config.is_api_configured() is False

    @patch.dict(os.environ, {
        'BINANCE_TESTNET_API_KEY': 'DuMmY_key',
        'BINANCE_TESTNET_API_SECRET': 'valid_secret'
    }, clear=True)
    def test_testnet_dummy_case_insensitive(self):
        config = TraderConfig(trader_mode='testnet')
        assert config.is_api_configured() is False