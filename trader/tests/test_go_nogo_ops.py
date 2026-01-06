#!/usr/bin/env python3
"""
Test for go_nogo operations check.
"""

import tempfile
import time
from pathlib import Path
import pytest
from trader.go_nogo import check_go_nogo
from trader.config import BASE_DIR


class TestGoNogoOps:
    def test_operations_pass_when_ops_cleanup_present(self, tmp_path, monkeypatch):
        """ops_cleanup lines present => operations PASS"""
        # Create temp logs dir at BASE_DIR.parent / scripts / logs
        # Since BASE_DIR will be tmp_path, logs_dir = tmp_path.parent / "scripts" / "logs"
        logs_dir = tmp_path.parent / "scripts" / "logs"
        logs_dir.mkdir(parents=True)

        # Create a log file with ops_cleanup lines
        log_file = logs_dir / "daily_run_20260105_230000.log"
        log_content = """
[STEP] Starting daily run
[STEP] ops_cleanup
Some other log lines
[GUARD] ops_cleanup done
[STEP] Finished
        """
        log_file.write_text(log_content)

        # Mock BASE_DIR and env
        monkeypatch.setenv('TRADER_MODE', 'paper')
        from trader import config
        original_base = config.BASE_DIR
        try:
            config.BASE_DIR = tmp_path
            import trader.go_nogo
            trader.go_nogo.BASE_DIR = tmp_path

            results = check_go_nogo()
            assert results["checks"]["operations"] is True
        finally:
            config.BASE_DIR = original_base
            trader.go_nogo.BASE_DIR = original_base

    def test_operations_fail_when_ops_cleanup_missing(self, tmp_path, monkeypatch):
        """ops_cleanup lines missing => operations FAIL"""
        # Create temp logs dir
        logs_dir = tmp_path.parent / "scripts" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create a log file without ops_cleanup lines
        log_file = logs_dir / "daily_run_20260105_230000.log"
        log_content = """
[STEP] Starting daily run
Some other log lines
[GUARD] Something else
[STEP] Finished
        """
        log_file.write_text(log_content)

        # Mock BASE_DIR
        monkeypatch.setenv('TRADER_MODE', 'paper')
        from trader import config
        original_base = config.BASE_DIR
        try:
            config.BASE_DIR = tmp_path
            import trader.go_nogo
            trader.go_nogo.BASE_DIR = tmp_path

            results = check_go_nogo()
            assert results["checks"]["operations"] is False
        finally:
            config.BASE_DIR = original_base
            trader.go_nogo.BASE_DIR = original_base

    def test_operations_fail_when_no_logs(self, tmp_path, monkeypatch):
        """No logs dir => operations FAIL"""
        # Ensure logs dir does not exist
        logs_dir = tmp_path.parent / "scripts" / "logs"
        if logs_dir.exists():
            import shutil
            shutil.rmtree(logs_dir)

        # Mock BASE_DIR
        monkeypatch.setenv('TRADER_MODE', 'paper')
        from trader import config
        original_base = config.BASE_DIR
        try:
            config.BASE_DIR = tmp_path
            import trader.go_nogo
            trader.go_nogo.BASE_DIR = tmp_path

            results = check_go_nogo()
            assert results["checks"]["operations"] is False
        finally:
            config.BASE_DIR = original_base
            trader.go_nogo.BASE_DIR = original_base

    def test_operations_fail_when_log_too_old(self, tmp_path, monkeypatch):
        """Log older than 24 hours => operations FAIL"""
        # Create temp logs dir
        logs_dir = tmp_path.parent / "scripts" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create old log file
        log_file = logs_dir / "daily_run_20260104_230000.log"
        log_content = """
[STEP] ops_cleanup
[GUARD] ops_cleanup done
        """
        log_file.write_text(log_content)

        # Set mtime to more than 24 hours ago
        old_time = time.time() - 25 * 3600
        log_file.touch()
        os = __import__('os')
        os.utime(str(log_file), (old_time, old_time))

        # Mock BASE_DIR
        monkeypatch.setenv('TRADER_MODE', 'paper')
        from trader import config
        original_base = config.BASE_DIR
        try:
            config.BASE_DIR = tmp_path
            import trader.go_nogo
            trader.go_nogo.BASE_DIR = tmp_path

            results = check_go_nogo()
            assert results["checks"]["operations"] is False
        finally:
            config.BASE_DIR = original_base
            trader.go_nogo.BASE_DIR = original_base