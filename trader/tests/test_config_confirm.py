#!/usr/bin/env python3
"""
Test for TraderConfig confirm/armed logic.
"""

import os
import pytest
from trader.config import TraderConfig


class TestConfigConfirm:
    def test_live_armed_true_when_live_dry_false_confirm_required(self, monkeypatch):
        """mode=live, dry_run=false, confirm==REQUIRED => True"""
        monkeypatch.setenv('ENV', 'prod')
        # Mock env vars to avoid interference
        monkeypatch.setenv('TRADER_DRY_RUN', 'false')
        monkeypatch.setenv('TRADER_LIVE_CONFIRM', TraderConfig.CONFIRM_REQUIRED)
        monkeypatch.setenv('TRADER_MODE', 'live')
        monkeypatch.setenv('TRADER_EXCHANGE_ENV', 'live')
        config = TraderConfig(
            trader_mode='live',
            dry_run=False,
            trader_live_confirm="I_UNDERSTAND_LIVE_TRADING_RISK"
        )
        assert config.is_live_armed is True

    def test_live_armed_false_when_live_dry_false_confirm_wrong(self, monkeypatch):
        """mode=live, dry_run=false, confirm!=REQUIRED => False"""
        monkeypatch.setenv('ENV', 'prod')
        monkeypatch.setenv('TRADER_DRY_RUN', 'false')
        monkeypatch.setenv('TRADER_LIVE_CONFIRM', 'wrong_confirm')
        monkeypatch.setenv('TRADER_MODE', 'live')
        monkeypatch.setenv('TRADER_EXCHANGE_ENV', 'live')
        config = TraderConfig(
            trader_mode='live',
            dry_run=False,
            trader_live_confirm="wrong_confirm"
        )
        assert config.is_live_armed is False

    def test_live_armed_false_when_live_dry_true_confirm_required(self, monkeypatch):
        """mode=live, dry_run=true, confirm==REQUIRED => False (dry_run overrides)"""
        monkeypatch.setenv('ENV', 'prod')
        monkeypatch.setenv('TRADER_DRY_RUN', 'true')
        monkeypatch.setenv('TRADER_LIVE_CONFIRM', TraderConfig.CONFIRM_REQUIRED)
        monkeypatch.setenv('TRADER_MODE', 'live')
        monkeypatch.setenv('TRADER_EXCHANGE_ENV', 'live')
        config = TraderConfig(
            trader_mode='live',
            dry_run=True,
            trader_live_confirm="I_UNDERSTAND_LIVE_TRADING_RISK"
        )
        assert config.is_live_armed is False

    def test_live_armed_false_when_testnet(self, monkeypatch):
        """mode=testnet => False"""
        monkeypatch.setenv('ENV', 'prod')
        monkeypatch.setenv('TRADER_DRY_RUN', 'false')
        monkeypatch.setenv('TRADER_LIVE_CONFIRM', TraderConfig.CONFIRM_REQUIRED)
        monkeypatch.setenv('TRADER_MODE', 'testnet')
        monkeypatch.setenv('TRADER_EXCHANGE_ENV', 'testnet')
        config = TraderConfig(
            trader_mode='testnet',
            dry_run=False,
            trader_live_confirm="I_UNDERSTAND_LIVE_TRADING_RISK"
        )
        assert config.is_live_armed is False

    def test_live_armed_false_when_paper(self, monkeypatch):
        """mode=paper => False"""
        monkeypatch.setenv('ENV', 'prod')
        monkeypatch.setenv('TRADER_DRY_RUN', 'false')
        monkeypatch.setenv('TRADER_LIVE_CONFIRM', TraderConfig.CONFIRM_REQUIRED)
        monkeypatch.setenv('TRADER_MODE', 'paper')
        monkeypatch.setenv('TRADER_EXCHANGE_ENV', 'testnet')
        config = TraderConfig(
            trader_mode='paper',
            dry_run=False,
            trader_live_confirm="I_UNDERSTAND_LIVE_TRADING_RISK"
        )
        assert config.is_live_armed is False
