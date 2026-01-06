import pytest
from ..strategies.ma_cross import calculate_ma_cross_signal
from ..paper_engine import OHLCV

def test_ma_cross_up():
    # Data that crosses up
    ohlcv: list[OHLCV] = [
        (1000, 100, 100, 100, 100, 100),  # t=0
        (2000, 100, 100, 100, 100, 100),  # t=1
        (3000, 100, 100, 100, 100, 100),  # t=2
        (4000, 100, 100, 100, 100, 100),  # t=3
        (5000, 100, 100, 100, 100, 100),  # t=4
        (6000, 105, 105, 105, 105, 105),  # t=5: short MA starts rising
        (7000, 110, 110, 110, 110, 110),  # t=6
        (8000, 115, 115, 115, 115, 110),  # t=7: cross up
    ]
    target_pos, reason, prev_diff = calculate_ma_cross_signal(ohlcv, 3, 5)
    assert target_pos == 1
    assert reason == "ma_cross_up"

def test_ma_cross_down():
    # Data that crosses down
    ohlcv: list[OHLCV] = [
        (1000, 110, 110, 110, 110, 110),  # t=0
        (2000, 110, 110, 110, 110, 110),  # t=1
        (3000, 110, 110, 110, 110, 110),  # t=2
        (4000, 110, 110, 110, 110, 110),  # t=3
        (5000, 110, 110, 110, 110, 110),  # t=4
        (6000, 105, 105, 105, 105, 105),  # t=5
        (7000, 100, 100, 100, 100, 100),  # t=6: cross down
    ]
    target_pos, reason, prev_diff = calculate_ma_cross_signal(ohlcv, 3, 5)
    assert target_pos == 0
    assert reason == "ma_cross_down"

def test_no_signal():
    # Flat data, no cross
    ohlcv: list[OHLCV] = [
        (1000, 100, 100, 100, 100, 100),
        (2000, 100, 100, 100, 100, 100),
        (3000, 100, 100, 100, 100, 100),
        (4000, 100, 100, 100, 100, 100),
        (5000, 100, 100, 100, 100, 100),
    ]
    target_pos, reason, prev_diff = calculate_ma_cross_signal(ohlcv, 3, 5)
    assert target_pos == -1
    assert reason == "no_signal"

def test_invalid_params():
    ohlcv = [(1000, 100, 100, 100, 100, 100)]
    with pytest.raises(ValueError):
        calculate_ma_cross_signal(ohlcv, 0, 5)
    with pytest.raises(ValueError):
        calculate_ma_cross_signal(ohlcv, 5, 5)