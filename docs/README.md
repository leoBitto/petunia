# 💸 Money Trading System

Automated trading data pipeline & decision support system. Fetches market data, executes technical strategies, and manages portfolio risk — featuring a hybrid Docker architecture and "Shadow Execution".

---

## 📊 Status

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Last Update:** December 2025  
**Version:** 0.4.0-alpha (Dev)  
**Tracked Tickers:** 33  

---

## 🧩 Overview

**Money** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution.

- **Hybrid Architecture:** Python application runs on host for I/O speed, Database runs containerized for stability.
- **Smart Sync:** Automatically fetches OHLC data and synchronizes manual trades via "Shadow Execution" logic.
- **Strategy Engine:** Extensible Technical Analysis modules (e.g., RSI Mean Reversion) using `pandas-ta`.
- **Risk First:** Core focus on Position Sizing and ATR-based Stop Loss management.
- **Backtesting:** Event-driven engine to simulate strategies on historical data.

---

## ⚙️ Project Structure

```text
money/
├── services/                 # Entry points
│   ├── daily_run.py          # Daily sync & mark-to-market
│   ├── weekly_run.py         # Strategy execution & reporting
│   └── backtest.py           # Historical simulation engine
├── src/                      # Core Logic Library
│   ├── database_manager.py   # PostgreSQL Wrapper (UPSERT logic)
│   ├── portfolio_manager.py  # In-Memory Portfolio & Trade Logic
│   ├── risk_manager.py       # Position Sizing & Stop Loss Calculator
│   ├── strategy_base.py      # Abstract Strategy Interface
│   └── strategies/           # Concrete implementations (RSI, etc.)
├── data/                     # Local Persistence
│   ├── db/                   # PostgreSQL Docker Volume
│   └── orders/               # Pending orders (JSON) for shadow sync
├── config/                   # Configuration files
├── manager.sh                # 🛠️ Unified Management Script
└── docker-compose.yml        # Infrastructure Definition (PostgreSQL)

```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

* Linux Environment (Debian/Ubuntu recommended)
* Docker & Docker Compose
* Python 3.11+
* `jq` (installed automatically by setup script)

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

### 4️⃣ Run

Start the infrastructure (Database Container):

```bash
./manager.sh start

```

Check status:

```bash
./manager.sh status

```

---

## 🧠 Workflow

### 🟢 Daily Routine (Monday - Friday)

* Runs `services/daily_run.py`.
* Updates OHLC data from Yahoo Finance.
* **Mark-to-Market:** Updates portfolio value based on daily Close.
* **Shadow Sync:** Converts pending orders into executed trades if price conditions were met.

### 🔴 Weekly Routine (Friday/Weekend)

* Runs `services/weekly_run.py`.
* **Strategy:** Executes Technical Analysis (e.g., RSI Mean Reversion).
* **Risk:** Calculates Position Size (2% Rule) & Stop Loss (2x ATR).
* **Report:** Generates a report for manual execution on the broker.

---

## 🧭 Roadmap

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Infrastructure** | `manager.sh`, Dockerized PostgreSQL, Secret Manager |
| ✅ | **DriveManager** | Google Sheets access & Universe loading |
| ✅ | **DatabaseManager** | Robust PostgreSQL wrapper with UPSERT support |
| ✅ | **PortfolioManager** | In-memory state management (Cash, Positions, Trades) |
| ✅ | **StrategyEngine** | Base class + RSI Strategy (pandas-ta) |
| ✅ | **RiskManager** | ATR-based sizing, Stop Loss, Cash Management |
| ✅ | **Backtester** | Event-driven simulation engine with Equity Curve |
| ⏳ | **Services** | Daily/Weekly orchestrators (In Progress) |
| ⏳ | **Reporter** | Automated weekly reporting |

---

## 📄 License

Released under the **MIT License**.
© 2025 Leonardo Bitto

---

## 📚 Documentation

Detailed documentation is currently maintained within the code `docstrings` and in the `docs/` folder.

