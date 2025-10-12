
```markdown
# 💸 Money Trading System

Automated trading data pipeline for fetching, analyzing, and generating trading signals — with Google Sheets integration and `systemd` scheduling.

---

## 📊 Status

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Last Commit](https://img.shields.io/github/last-commit/leoBitto/money)

**Last Update:** October 12, 2025  
**Version:** 0.2.0  
**Tracked Tickers:** 33  

---

## 🧩 Overview

**Money** is a modular trading system designed to:
- Fetch and synchronize financial data from Google Sheets and Yahoo Finance  
- Store and update data automatically  
- Run technical trading strategies  
- Produce automated reports through `systemd` timers  

---

## ⚙️ Project Structure

```

money/
├── src/
│   ├── logger.py             # Centralized logging
│   ├── drive_manager.py      # Google Sheets / Secret Manager
│   └── ...
├── scripts/
│   ├── tester.py             # Manual testing
│   ├── daily_run.py          # Daily scheduled run
│   └── weekly_run.py         # Weekly reporting
├── config/
│   └── config.py             # Central configuration
├── docs/
│   └── DEV_NOTES.md          # Developer notes & setup guide
└── logs/                     # Runtime logs

````

---

## 🚀 Quick Start

### 1️⃣ Setup Environment
```bash
git clone https://github.com/leoBitto/money.git
cd money
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
````

### 2️⃣ Authenticate with Google Cloud

Place your **service account JSON** under:

```
docs/service_account.json
```

Then export the credential path:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/docs/service_account.json"
```

---

## 🧠 Example Usage

```python
from src.drive_manager import DriveManager

dm = DriveManager()
tickers = dm.get_universe_tickers()
print(tickers)
```

Typical log output:

```
2025-10-12 15:51:51 | INFO | DriveManager | Google Sheets authentication completed.
2025-10-12 15:51:54 | INFO | DriveManager | Universe sheet loaded: 33 tickers found.
```

---

## 🪶 Philosophy

* Simple and modular architecture
* Centralized configuration
* Unified logging
* One responsibility per module
* Fully compatible with `systemd` automation

---

## 🧭 Roadmap

| Status | Module          | Description                           |
| :----: | :-------------- | :------------------------------------ |
|    ✅   | DriveManager    | Google Sheets & Secret Manager access |
|   🔄   | DatabaseManager | PostgreSQL connection & schema        |
|    ⏳   | DataFetcher     | Market data via Yahoo Finance         |
|    ⏳   | StrategyEngine  | Trading signal generation             |
|    ⏳   | Reporter        | Weekly summaries & reports            |

---

## 📄 License

Released under the **MIT License**.
© 2025 Leonardo Bitto

---

## 📚 Documentation

See [`docs/DEV_NOTES.md`](./docs/DEV_NOTES.md) for:

* Environment setup
* Google Cloud configuration
* Systemd service examples
* Development guidelines

---

```

