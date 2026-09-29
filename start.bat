@echo off
echo =======================================
echo Autonomous AI Trading System Setup
echo =======================================

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

IF NOT EXIST ".env" (
    echo Creating default configuration...
    copy .env.example .env
)

echo Initializing database...
alembic upgrade head

echo.
echo =======================================
echo Setup Complete! Starting Dashboard...
echo =======================================
python main.py
pause
