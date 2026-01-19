import pytest
import os
import numpy as np
from pathlib import Path
import importlib.util

def _load_plotter():
    path = Path(__file__).resolve().parents[1] / "src" / "plotter.py"
    spec = importlib.util.spec_from_file_location("trend_illustrator_plotter", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

_plotter = _load_plotter()
plot_trend = _plotter.plot_trend

def test_plot_trend(tmp_path):
    # Test data
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([2, 4, 6, 8, 10])
    trend_x = x
    trend_y = y

    # Output file path
    output_file = tmp_path / "test_plot.png"

    # Call plot function
    plot_trend(x, y, trend_x, trend_y, str(output_file))

    # Check that file was created
    assert output_file.exists()

    # Check that file is not empty
    assert output_file.stat().st_size > 0