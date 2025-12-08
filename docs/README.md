Certamente\! È fondamentale tenere la documentazione allineata con il codice, specialmente dopo i cambiamenti infrastrutturali (Docker, `manager.sh`) e architetturali (`services/` vs `scripts/`) che abbiamo introdotto.

Ecco una versione aggiornata e pulita del **README.md** che riflette lo stato attuale del branch `rebase` e le nuove procedure di setup.

````markdown
# 💸 Money Trading System

Automated trading data pipeline & decision support system. Fetches market data, executes technical strategies, and manages portfolio risk — featuring a hybrid Docker architecture and Google Sheets reporting.

---

## 📊 Status

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Last Update:** December 2025  
**Version:** 0.3.0-alpha  
**Tracked Tickers:** 33  

---

## 🧩 Overview

**Money** is a modular trading system designed to act as a "Shadow Automator" for retail trading:
- **Hybrid Architecture:** Python application runs on host for performance/IO, Database runs containerized for stability.
- **Smart Sync:** Automatically fetches OHLC data and synchronizes manual trades via "Shadow Execution".
- **Strategy Engine:** Extensible Technical Analysis modules (RSI, Mean Reversion) using `pandas-ta`.
- **Risk First:** Core focus on Position Sizing and ATR-based Stop Loss management.

---

## ⚙️ Project Structure

```text
money/
├── services/                 # Entry points (Systemd triggers)
│   ├── daily_run.py          # Daily sync & mark-to-market
│   └── weekly_run.py         # Strategy execution & reporting
├── src/                      # Core Logic Library
│   ├── database_manager.py   # PostgreSQL Wrapper (UPSERT logic)
│   ├── portfolio_manager.py  # In-Memory Portfolio Logic
│   ├── strategy_base.py      # Abstract Strategy Class
│   └── ...
├── data/                     # Local Data Persistence
│   ├── db/                   # PostgreSQL Docker Volume
│   └── orders/               # Pending orders (JSON) for shadow sync
├── config/                   # Configuration files
├── manager.sh                # 🛠️ Unified Management Script (Setup, Start, Logs)
└── docker-compose.yml        # Infrastructure Definition (PostgreSQL)
````

-----

## 🚀 Quick Start

### 1️⃣ Prerequisites

  * Linux Environment (Debian/Ubuntu recommended)
  * Docker & Docker Compose
  * Python 3.11+
  * `jq` (installed automatically by setup script if possible)

### 2️⃣ Setup

The project includes a unified manager script to handle environment setup, dependencies, and infrastructure.

```bash
git clone [https://github.com/leoBitto/money.git](https://github.com/leoBitto/money.git)
cd money

# Initializes venv, installs requirements, creates directory structure
./manager.sh setup
```

### 3️⃣ Configuration

Place your **Google Service Account** JSON key in:
`docs/service_account.json`

(This key is used to access Google Secret Manager for DB credentials and Google Sheets).

### 4️⃣ Run

Start the infrastructure (Database Container):

```bash
./manager.sh start
```

Check status:

```bash
./manager.sh status
```

-----

## 🧠 Workflow

### 🟢 Daily Routine (Monday - Thursday)

  * Runs `services/daily_run.py`.
  * Updates OHLC data from Yahoo Finance.
  * Syncs Portfolio state (Mark-to-Market).
  * Checks for "Shadow Orders" (trades executed manually but not yet logged).

### 🔴 Weekly Routine (Friday)

  * Runs `services/weekly_run.py`.
  * Executes Strategies (e.g., RSI Mean Reversion).
  * Risk Manager calculates Position Size & Stops.
  * Generates a Report (Google Sheet) for weekend review.

-----

## 🧭 Roadmap

| Status | Module | Description |
| :---: | :--- | :--- |
| ✅ | **Infrastructure** | `manager.sh`, Dockerized PostgreSQL, Secret Manager |
| ✅ | **DriveManager** | Google Sheets access & Universe loading |
| ✅ | **DatabaseManager** | Robust PostgreSQL wrapper with UPSERT support |
| ✅ | **PortfolioManager** | In-memory state management (Cash, Positions, History) |
| ✅ | **DataFetcher** | YFinance wrapper with normalization |
| 🔄 | **StrategyEngine** | Base class defined. Implementing RSI/Mean Reversion |
| ⏳ | **RiskManager** | ATR-based sizing & Stop Loss logic (Next Step) |
| ⏳ | **Reporter** | Automated weekly reporting |

-----

## 📄 License

Released under the **MIT License**.
© 2025 Leonardo Bitto

-----

## 📚 Documentation

See [`docs/DEV_NOTES.md`](https://www.google.com/search?q=./docs/DEV_NOTES.md) for detailed architectural decisions and developer guides.

```

