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
**Version:** 1.1.0 (Dashboard Enabled)  
**Tracked Tickers:** Dynamic (GSheet)  

---

## 🧩 Overview

**Petunia** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution via Google Sheets.

- **Containerized Architecture:** Both the Application (Python) and the Database (PostgreSQL) run in isolated Docker containers for maximum stability and reproducibility.
- **Interactive Dashboard:** A Streamlit-based UI to monitor portfolio performance, visualize data, and manage system operations (Init/Reset).
- **Smart Sync:** Automatically fetches OHLC data (Yahoo Finance) and synchronizes manual trades via "Shadow Execution" logic.
- **Risk First:** Core focus on Position Sizing and ATR-based Stop Loss management.
- **CI/CD Integration:** Automated testing and deployment pipelines via GitHub Actions.

---

## ⚙️ Project Structure

```text
petunia/
├── .github/workflows/        # CI/CD Pipelines (Linting & Deploy)
├── dashboard/                # 📊 User Interface (Streamlit)
│   ├── home.py               # Dashboard Entry Point
│   └── components/           # UI Widgets & plotting logic
├── services/                 # Entry points (executed inside Docker)
│   ├── daily_run.py          # Daily sync & mark-to-market
│   ├── weekly_run.py         # Strategy execution & reporting
│   └── init_db.py            # 🛠️ Database Schema & Bootstrap
├── src/                      # Core Logic Library
│   ├── database_manager.py   # PostgreSQL Wrapper (psycopg3)
│   ├── portfolio_manager.py  # In-Memory Portfolio & Trade Logic
│   ├── risk_manager.py       # Position Sizing & Stop Loss Calculator
│   └── drive_manager.py      # Google Sheets & Local Auth
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
# (Edit .env with your DB credentials and Sheet IDs)

# 2. Add Credentials
mkdir -p config/credentials
cp /path/to/your/key.json config/credentials/service_account.json

# 3. Build Infrastructure
./manager.sh setup

```

### 3️⃣ Run & Initialize

Start the infrastructure (Database Container):

```bash
./manager.sh start
# Wait 10 seconds for Postgres to wake up...

```

**Launch the Dashboard to Initialize:**
Unlike previous versions, system initialization is now handled via the UI.

1. Open your browser at `http://localhost:8501`.
2. Navigate to the **"control panel"** section.
3. Click **"Reset Database Schema"** to create schemas.
4. Click **"Start Data Fetch"** to bootstrap historical data.

### 4️⃣ Manual Operations

```bash
# Daily Routine (Market Data Sync & Portfolio Update)
./manager.sh daily

# Weekly Routine (Strategy Execution & Reporting)
./manager.sh weekly

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

### v1.x - Expansion & Testing (Current Focus)

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Core v1.0** | Stable Docker Architecture, RSI Strategy, Risk Manager |
| ✅ | **Dashboard** | Streamlit Frontend for visual analytics & system management |
| 🔄 | **Strategies** | Adding Trend Following (EMA) and Breakout strategies |
| ⏳ | **Testing** | Extensive Unit & Integration Tests (PyTest) |
| ⏳ | **Universe** | Scaling tracked universe to 100+ tickers |

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
👉 **[docs/OPERATIONAL_GUIDE.md](https://www.google.com/search?q=docs/OPERATIONAL_GUIDE.md)**
