from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./trading.db"

    # API Keys
    MARKET_DATA_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    BROKER_API_KEY: Optional[str] = None
    BROKER_API_SECRET: Optional[str] = None

    # Trading Config
    TRADING_MODE: str = "PAPER_TRADING"
    MAX_RISK_PER_TRADE: float = 0.01
    MAX_DAILY_LOSS: float = 0.05
    MAX_DRAWDOWN: float = 0.10
    MAX_LEVERAGE: float = 1.0

    # AI Config
    AI_MODEL_PROVIDER: str = "local"
    AI_MODEL_NAME: str = "mistral-7b"
    AI_TEMPERATURE: float = 0.7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
