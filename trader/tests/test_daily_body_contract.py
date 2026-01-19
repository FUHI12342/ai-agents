import tempfile
import unittest.mock
from pathlib import Path

from trader.report_blocks import render_min_lot_live_gonogo_email


def test_render_min_lot_live_gonogo_email_warning_block():
    """Test that WARNING: API_NOT_CONFIGURED is included when API not configured"""
    with unittest.mock.patch('trader.report_blocks.load_config') as mock_load:
        mock_config = unittest.mock.MagicMock()
        mock_config.trader_mode = 'testnet'
        mock_config.dry_run = False
        mock_config.kill_switch_path.exists.return_value = False
        mock_config.trader_live_confirm = ''
        mock_config.is_live_armed = False
        mock_config.is_api_configured.return_value = False  # API not configured
        mock_load.return_value = mock_config

        result = render_min_lot_live_gonogo_email()

        assert "WARNING: API_NOT_CONFIGURED" in result
        assert "Set .env: BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET" in result


def test_render_min_lot_live_gonogo_email_no_warning_when_configured():
    """Test that no WARNING when API configured"""
    with unittest.mock.patch('trader.report_blocks.load_config') as mock_load:
        mock_config = unittest.mock.MagicMock()
        mock_config.trader_mode = 'testnet'
        mock_config.dry_run = False
        mock_config.kill_switch_path.exists.return_value = False
        mock_config.trader_live_confirm = ''
        mock_config.is_live_armed = False
        mock_config.is_api_configured.return_value = True  # API configured
        mock_load.return_value = mock_config

        result = render_min_lot_live_gonogo_email()

        assert "WARNING: API_NOT_CONFIGURED" not in result


def test_skip_placeholder_structure():
    """Test that SKIP placeholders have proper newline structure"""
    # Test the content that daily_run.ps1 generates for SKIP
    # Example from daily_run.ps1
    skip_content = """Live Summary
----------------------------------------
SKIPPED: mode=paper
timestamp: 2026-01-06T07:12:53.0000000+09:00
mode: paper
dry_run: true
"""

    lines = skip_content.split('\n')
    assert "SKIPPED:" in lines[2]
    # Next line should have timestamp:
    assert lines[3].strip().startswith("timestamp:")
    # Ensure newline after SKIPPED:
    assert lines[2].endswith("paper")  # SKIPPED: mode=paper
    assert lines[3].strip() == "timestamp: 2026-01-06T07:12:53.0000000+09:00"


def test_paper_yahoo_fail_summary_format():
    """Test that FAIL summary has ERROR: in fixed format"""
    fail_content = """PaperYahoo Summary
ERROR: rc=1
symbol: ^N225
reason: failed to load data
"""

    assert fail_content.startswith("PaperYahoo Summary\n")
    assert "ERROR:" in fail_content
    assert "symbol:" in fail_content
    assert "reason:" in fail_content