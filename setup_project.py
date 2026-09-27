import os

directories = [
    "app",
    "app/core",
    "app/data",
    "app/data/market",
    "app/data/news",
    "app/data/economic",
    "app/features",
    "app/analysis",
    "app/analysis/technical",
    "app/analysis/fundamental",
    "app/analysis/quantitative",
    "app/analysis/sentiment",
    "app/analysis/microstructure",
    "app/ai",
    "app/strategies",
    "app/risk",
    "app/portfolio",
    "app/execution",
    "app/orders",
    "app/positions",
    "app/reconciliation",
    "app/backtest",
    "app/replay",
    "app/paper",
    "app/monitoring",
    "app/monitoring/dashboard",
    "app/monitoring/dashboard/templates",
    "app/monitoring/dashboard/static",
    "app/monitoring/dashboard/components",
    "app/monitoring/dashboard/websocket",
    "app/alerts",
    "app/database",
    "app/security",
    "app/config",
    "tests",
    "tests/unit",
    "tests/integration",
    "tests/backtest",
    "tests/stress",
    "tests/execution",
    "scripts",
    "migrations",
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    # create an empty __init__.py in all python packages
    if "tests" in directory or "app" in directory:
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                pass

print("Directories created successfully!")
