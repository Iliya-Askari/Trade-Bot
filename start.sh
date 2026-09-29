#!/bin/bash
echo "======================================="
echo "Autonomous AI Trading System Setup"
echo "======================================="

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creating default configuration..."
    cp .env.example .env
fi

echo "Initializing database..."
alembic upgrade head

echo ""
echo "======================================="
echo "Setup Complete! Starting Dashboard..."
echo "======================================="
python3 main.py
