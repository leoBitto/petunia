# 💸 Money Trading System

Automated trading data pipeline & decision support system. Fetches market data, executes technical strategies, and manages portfolio risk — featuring a fully Dockerized architecture and "Shadow Execution".

---

## 📊 Status

![CI Status](https://github.com/leoBitto/money/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Last Update:** December 2025  
**Version:** 0.5.0 (Dev)  
**Tracked Tickers:** 33  

---

## 🧩 Overview

**Money** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution via Google Sheets.

- **Containerized Architecture:** Both the Application (Python) and the Database (PostgreSQL) run in isolated Docker containers for maximum stability and reproducibility.
- **Smart Sync:** Automatically fetches OHLC data and synchronizes manual trades via "Shadow Execution" logic.
- **Strategy Engine:** Extensible Technical Analysis modules (e.g., RSI Mean Reversion) using `pandas-ta`.
- **Risk First:** Core focus on Position Sizing and ATR-based Stop Loss management.
- **CI/CD Integration:** Automated testing and deployment pipelines via GitHub Actions.

---

## ⚙️ Project Structure

```text
money/
├── .github/workflows/        # CI/CD Pipelines (Linting & Deploy)
├── services/                 # Entry points (executed inside Docker)
│   ├── daily_run.py          # Daily sync & mark-to-market
│   ├── weekly_run.py         # Strategy execution & reporting
│   └── backtest.py           # Historical simulation engine
├── src/                      # Core Logic Library
│   ├── database_manager.py   # PostgreSQL Wrapper
│   ├── portfolio_manager.py  # In-Memory Portfolio & Trade Logic
│   ├── risk_manager.py       # Position Sizing & Stop Loss Calculator
│   └── drive_manager.py      # Google Sheets & Secret Handling
├── config/                   # Configuration & Credentials
│   ├── config.py             # Env var loader
│   └── credentials/          # Service Account JSON (Local only)
├── data/                     # Local Persistence
│   └── db/                   # PostgreSQL Docker Volume
├── Dockerfile                # App Image Definition
├── manager.sh                # 🛠️ Unified Management Script
└── docker-compose.yml        # Full Infrastructure Definition

```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

* Docker & Docker Compose
* A Google Cloud Service Account (JSON Key)

### 2️⃣ Setup

The project includes a unified manager script to handle environment setup and container building.

```bash
git clone [https://github.com/leoBitto/money.git](https://github.com/leoBitto/money.git)
cd money

# 1. Configure Environment
cp .env.example .env
# (Edit .env with your DB password and Sheet IDs)

# 2. Add Credentials
mkdir -p config/credentials
cp /path/to/your/key.json config/credentials/service_account.json

# 3. Build Infrastructure
./manager.sh setup

```

### 3️⃣ Run

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
* **Shadow Sync:** Reads the **"Orders" Google Sheet**. If a pending order's price condition is met, it executes the trade in the local database and removes it from the Sheet.

### 🔴 Weekly Routine (Friday/Weekend)

* Runs `services/weekly_run.py`.
* **Strategy:** Executes Technical Analysis (e.g., RSI Mean Reversion).
* **Risk:** Calculates Position Size (2% Rule) & Stop Loss (2x ATR).
* **Report:** Writes proposed orders directly to the **"Orders" Google Sheet** for human review and manual broker execution.

---

## 🧭 Roadmap

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Infrastructure** | `manager.sh`, Full Dockerization, CI/CD Pipelines |
| ✅ | **DriveManager** | Google Sheets for Universe loading & Order Sync |
| ✅ | **DatabaseManager** | Robust PostgreSQL wrapper with UPSERT support |
| ✅ | **PortfolioManager** | In-memory state management (Cash, Positions, Trades) |
| ✅ | **StrategyEngine** | Base class + RSI Strategy (pandas-ta) |
| ✅ | **RiskManager** | ATR-based sizing, Stop Loss, Cash Management |
| ✅ | **Services** | Daily/Weekly orchestrators linked to GSheets |
| ✅ | **Backtester** | Event-driven simulation engine with Equity Curve |
| ⏳ | **Dashboard** | Streamlit Frontend for visual analytics (Next Step) |

---

## 📄 License

Released under the **MIT License**.
© 2025 Leonardo Bitto

---

## 📚 Documentation

For detailed operational guides, security flows, and architecture diagrams, see:
👉 **[docs/OPERATIONAL_GUIDE.md](https://www.google.com/search?q=docs/OPERATIONAL_GUIDE.md)**
