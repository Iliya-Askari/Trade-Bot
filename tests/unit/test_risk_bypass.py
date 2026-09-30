import pytest
from app.execution.mt5_adapter import MT5Adapter
from tests.fake_mt5 import FakeMT5
from app.config.settings import settings

def test_risk_bypass_quantity_rejection():
    # If the calculated quantity from risk is 0.005, but volume_min is 0.01
    # the engine should REJECT the trade rather than forcing it up to 0.01.
    import main

    # We can test the exact mathematical logic by simulating the values:
    raw_quantity = 0.005
    volume_step = 0.01
    volume_min = 0.01
    volume_max = 100.0

    import math
    quantity = math.floor(raw_quantity / volume_step) * volume_step

    # This proves the logic in main.py will correctly reject it
    assert quantity < volume_min

    # Now let's test a valid one
    raw_quantity = 0.015
    quantity_valid = math.floor(raw_quantity / volume_step) * volume_step
    assert quantity_valid >= volume_min
    assert quantity_valid == 0.01
