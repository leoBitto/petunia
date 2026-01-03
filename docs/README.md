<div align="center">
  <img src="images/petunia_logo.png" width="200" alt="Petunia Logo">
  <h1>Petunia Trading System</h1>
  <p><em>"Petunia" is a playful derivative of the Latin word <b>Pecunia</b> (money/wealth),<br>symbolizing organic growth in a digital financial environment.</em></p>
</div>

Automated trading data pipeline & decision support system. Fetches market data, executes technical strategies, and manages portfolio risk — featuring a fully Dockerized architecture, a visual Dashboard, and "Shadow Execution".

---

## 📊 Status

![CI Status](https://github.com/leoBitto/petunia/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Docker](https://img.shields.io/badge/docker-compose-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Last Update:** January 2026  
**Version:** 1.2.0 (Strategies & Testing)  
**Tracked Tickers:** 130+ (Dynamic via GSheet)  

---

## 🧩 Overview

**Petunia** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution via Google Sheets.

- **Containerized Architecture:** Both the Application (Python) and the Database (PostgreSQL) run in isolated Docker containers for maximum stability and reproducibility.
- **Interactive Dashboard:** A Streamlit-based UI to monitor portfolio performance, visualize data, and manage system operations.
- **Strategy Factory:** Modular strategy engine supporting Mean Reversion (RSI) and Trend Following (EMA Crossover) with standardized output contracts.
- **Robust Testing:** Full Pytest suite covering Unit Tests (Logic), Mocking (External APIs), and Integration Tests (Database).
- **Risk First:** Core focus on Position Sizing and ATR-based Stop Loss management.

---

## ⚙️ Project Structure

```text
petunia/
├── .github/workflows/        # CI/CD Pipelines (Linting & Testing)
├── dashboard/                # 📊 User Interface (Streamlit)
│   ├── home.py               # Dashboard Entry Point
│   └── components/           # UI Widgets & plotting logic
├── services/                 # Entry points (executed inside Docker)
│   ├── daily_run.py          # Daily sync & mark-to-market
│   ├── weekly_run.py         # Strategy execution & reporting
│   └── backtest.py           # Historical Simulation Engine
├── src/                      # Core Logic Library
│   ├── strategies/           # 🧠 Strategy Package (Factory Pattern)
│   │   ├── base.py           # Abstract Base Class
│   │   ├── ema.py            # Trend Following (EMA Crossover)
│   │   └── rsi.py            # Mean Reversion (RSI)
│   │   └── __init__.py       # Strategy Factory
│   ├── database_manager.py   # PostgreSQL Wrapper (psycopg3)
│   ├── portfolio_manager.py  # In-Memory Portfolio & Trade Logic
│   ├── risk_manager.py       # Position Sizing & Stop Loss Calculator
│   └── drive_manager.py      # Google Sheets & Local Auth
├── tests/                    # 🧪 Test Suite (Pytest)
│   ├── conftest.py           # Shared Fixtures (Golden Datasets, DB Integration)
│   ├── strategies/           # Strategy Logic & Contract Tests
│   └── test_core/            # Core Modules Unit/Integration Tests
├── config/                   # Configuration
│   ├── config.py             # Env var loader
│   └── credentials/          # Service Account JSON (Local volume)
├── data/                     # Local Persistence
│   └── db/                   # PostgreSQL Docker Volume (Managed by Docker)
├── Dockerfile                # App Image Definition
├── manager.sh                # 🛠️ Unified Management Script
└── docker-compose.yml        # Full Infrastructure Definition

```

---

## 🚀 Quick Start

### 1️⃣ Prerequisites

* Docker & Docker Compose (v2+)
* A Google Cloud Service Account (JSON Key) with Sheets API enabled.

### 2️⃣ Setup

The project includes a unified manager script to handle environment setup and container building.

```bash
git clone [https://github.com/leoBitto/petunia.git](https://github.com/leoBitto/petunia.git)
cd petunia

# 1. Configure Environment
cp .env.example .env

# 2. Add Credentials
mkdir -p config/credentials
cp /path/to/your/key.json config/credentials/service_account.json

# 3. Build Infrastructure
./manager.sh setup

```

### 3️⃣ Run & Initialize

Start the infrastructure:

```bash
./manager.sh start

```

**Launch the Dashboard to Initialize:**
Open `http://localhost:8501`, navigate to **"Control Panel"**, and click **"Reset Database Schema"** and **"Start Data Fetch"**.

### 4️⃣ Testing & Dev

Run the full test suite inside the isolated Docker container:

```bash
./manager.sh test

```

---

## 🧠 Workflow

### 🟢 Daily Routine (Monday - Friday)

* Runs `services/daily_run.py`.
* Updates OHLC data and Portfolio Valuation (Mark-to-Market).
* **Shadow Sync:** Executes pending orders from Google Sheets if limits are hit.

### 🔴 Weekly Routine (Weekend)

* Runs `services/weekly_run.py`.
* **Strategy Engine:** Selects active strategy via Config (Default: RSI).
* **Risk Manager:** Calculates Position Size (2% Rule) & Stop Loss.
* **Report:** Pushes new orders to Google Sheets for review.

---

## 🧭 Roadmap

### v1.x - Expansion & Testing (Current Focus)

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Core v1.0** | Stable Docker Architecture, Risk Manager |
| ✅ | **Testing** | Full PyTest Suite: Unit, Mocking, and DB Integration |
| ✅ | **Strategies** | Implemented Trend Following (EMA) & Mean Reversion (RSI) Logic |
| ✅ | **Universe** | Scaling tracked universe to 100+ tickers (In Progress) |
| 🔄 | **Service Integration** | Refactor `weekly_run` & `backtest` to use Strategy Factory |
| 🔄 | **Dynamic Config** | Allow Strategy selection via Frontend (DB-backed Settings) |


### v2.0 - Cloud Native & DevOps

| Status | Module | Description |
| --- | --- | --- |
| 🔮 | **IaC** | Terraform for GCP Infrastructure provisioning |
| 🔮 | **Cloud Deploy** | Production deployment on GCP Compute Engine |
| 🔮 | **Secret Mgr** | Migration to Google Secret Manager (No more .env) |
| 🔮 | **AI Agent** | LLM-based Market Sentiment Analysis integration |

---

## 📄 License

Released under the **MIT License**.
© 2026 Leonardo Bitto

---

## 📚 Documentation

For detailed operational guides, security flows, and architecture diagrams, see:
👉 **[docs/OPERATIONAL_GUIDE.md](https://www.google.com/search?q=./docs/OPERATIONAL_GUIDE.md)**
