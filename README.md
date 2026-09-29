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

## 🚀 1-Click Setup and Execution

We've radically simplified the setup process. You don't need to manually run commands.

### Windows
Double-click the `start.bat` file in the main folder.
*This will automatically create a virtual environment, install all dependencies, setup the database, and launch the web dashboard.*

### Mac / Linux
Run the following in your terminal:
```bash
chmod +x start.sh
./start.sh
```

## How to Trade
Once the dashboard opens in your browser (usually `http://127.0.0.1:8000`), you will see a massive **"START TRADING"** button. The trading loop runs entirely in the background, controlled directly from the UI. You do not need to run separate commands for paper/live trading anymore.

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
