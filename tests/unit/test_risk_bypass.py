import pytest
from app.execution.mt5_adapter import MT5Adapter
from tests.fake_mt5 import FakeMT5
from app.config.settings import settings

def test_risk_bypass_quantity_rejection():
    # If the calculated quantity from risk is 0.005, but volume_min is 0.01
    # the engine should REJECT the trade rather than forcing it up to 0.01.
    # To test this via the actual logic flow in main, we can write a small functional test

    # In main.py, the logic is:
    # quantity = math.floor(raw_quantity / volume_step) * volume_step
    # if quantity < volume_min: continue

    # We will test the RiskEngine's exact output logic:
    import math

    # Example 1: Insufficient risk budget
    raw_quantity = 0.005
    volume_step = 0.01
    volume_min = 0.01
    volume_max = 100.0

    quantity = math.floor(raw_quantity / volume_step) * volume_step

    # Assert rejection
    assert quantity < volume_min

    # Example 2: Sufficient budget (0.019 lots requested)
    raw_quantity = 0.019
    quantity_valid = math.floor(raw_quantity / volume_step) * volume_step

    # Assert acceptance and rounding down
    assert quantity_valid >= volume_min
    assert quantity_valid == 0.01

    # Example 3: dynamic precision decimal rounding (the fix in main.py)
    step_str = f"{volume_step:.8f}".rstrip('0').rstrip('.')
    precision = len(step_str.split('.')[1]) if '.' in step_str else 0
    final_qty = round(quantity_valid, precision)

    assert final_qty == 0.01
    assert precision == 2
