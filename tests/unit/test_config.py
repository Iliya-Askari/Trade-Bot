import os
from app.config.settings import Settings

def test_settings_load_defaults():
    # Ensure environment defaults are correct
    settings = Settings()
    assert settings.TRADING_MODE == "PAPER_TRADING"
    assert settings.MAX_LEVERAGE == 1.0
    assert settings.DATABASE_URL.startswith("sqlite")
