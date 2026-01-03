<div align="center">
  <img src="images/petunia_logo.png" width="600" alt="Petunia Logo">
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
**Version:** 1.2.0  
**Wiki:** [Complete Documentation](https://github.com/leoBitto/petunia/wiki)

---

## 🧩 Overview

**Petunia** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution via Google Sheets.

### Key Features
* 🐳 **Containerized Architecture:** Isolated Docker environments for App and Database (PostgreSQL).
* 📈 **Strategy Factory:** Plug-and-play strategy engine (Currently supporting **EMA Crossover** & **RSI Mean Reversion**).
* 🛡️ **Risk First:** Built-in Risk Manager enforcing the 2% Rule and ATR-based volatility stops.
* 🧪 **Robust Testing:** Full Pytest suite with mock services and integration tests.
* 📊 **Interactive Dashboard:** Streamlit UI for portfolio monitoring and system control.

---

## 🚀 Quick Start

### Prerequisites
* Docker & Docker Compose (v2+)
* Google Cloud Service Account (JSON Key)

### Installation

```bash
# 1. Clone & Config
git clone [https://github.com/leoBitto/petunia.git](https://github.com/leoBitto/petunia.git)
cd petunia
cp .env.example .env

# 2. Add Credentials
mkdir -p config/credentials
cp /path/to/your/key.json config/credentials/service_account.json

# 3. Build & Run
./manager.sh setup
./manager.sh start

```

Once running, access the Dashboard at **`http://localhost:8501`** to initialize the database.

---

## 📚 Documentation

Detailed documentation is available in the **[GitHub Wiki](https://www.google.com/url?sa=E&source=gmail&q=https://github.com/leoBitto/petunia/wiki)**.

* **[Strategy Playbook](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Strategy-Playbook):** Deep dive into EMA and RSI logic.
* **[Risk Management](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Risk-Management-Bible):** How position sizing works.
* **[Architecture](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Architecture-%26-Data-Flow):** System internals and data pipeline.
* **[Developer Guide](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Developer-Guide):** Project structure and contribution guidelines.

---

## 🧭 Roadmap

### v1.x - Expansion & Testing (Current Focus)

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Core v1.0** | Stable Docker Architecture, Risk Manager |
| ✅ | **Testing** | Full PyTest Suite: Unit, Mocking, and DB Integration |
| ✅ | **Strategies** | Implemented Trend Following (EMA) & Mean Reversion (RSI) Logic |
| 🔄 | **Dynamic Config** | Allow Strategy selection via Frontend (DB-backed Settings) |
| ⏳ | **Universe** | Scaling tracked universe to 100+ tickers (In Progress) |

### v2.0 - Cloud Native & DevOps

| Status | Module | Description |
| --- | --- | --- |
| 🔮 | **IaC** | Terraform for GCP Infrastructure provisioning |
| 🔮 | **Cloud Deploy** | Production deployment on GCP Compute Engine |
| 🔮 | **Secret Mgr** | Migration to Google Secret Manager (No more .env) |

---

## 📄 License

Released under the **MIT License**.
© 2026 Leonardo Bitto
