# Autonomous AI Trading System

## Architecture Overview
This is an event-driven autonomous trading system designed for robust execution, rigorous risk management, and modular extensibility. It implements a fully independent deterministic risk engine that overrides AI suggestions if they breach limits.

## Project Structure
- `app/` - Core application logic, including the FastAPI dashboard.
  - `config/` - Pydantic settings.
  - `core/` - Abstract interfaces.
  - `database/` - SQLAlchemy models and session.
  - `execution/` - Order submission and broker adapters.
  - `risk/` - Deterministic risk engine.
  - `monitoring/` - FastAPI Web Dashboard.
- `migrations/` - Alembic database migrations.
- `tests/` - Pytest suites.

## Setup Instructions (Windows 10/11)

1. **Clone the repository.**
2. **Create a virtual environment and install dependencies:**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and fill in your details (leave dummy keys for providers not yet connected).
   ```cmd
   copy .env.example .env
   ```
4. **Initialize the Database:**
   ```cmd
   alembic upgrade head
   ```

## Execution Commands

- **Run Dashboard:**
  ```cmd
  python main.py
  ```
- **Run Backtest:**
  ```cmd
  python main.py --mode backtest
  ```
- **Run Paper Trading:**
  ```cmd
  python main.py --mode paper
  ```
- **Run Live Trading:**
  ```cmd
  python main.py --mode live
  ```

## Known Limitations
- Broker Adapters are currently implemented as mock stubs.
- Market Data Adapters are currently stubbed.
- AI logic layers are stubbed.
- Complete frontend UI functionality relies on the `/api` definitions which are minimal in the current release.

## Recovery Procedures
If the database becomes corrupt or out-of-sync:
1. Delete `trading.db`.
2. Re-run `alembic upgrade head`.
3. Only resume paper or live trading once account reconciliation logs confirm parity.
