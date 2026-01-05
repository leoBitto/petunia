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
**Version:** 1.4.0 (Vectorized Engine & Fee-Adjusted Backtesting)
**Wiki:** [Complete Documentation](https://github.com/leoBitto/petunia/wiki)

---

## 🧩 Overview

**Petunia** is a modular trading system designed to act as a **"Shadow Automator"** for retail trading. It doesn't execute orders directly on the broker but manages the logic, risk, and accounting, syncing with manual execution via Google Sheets.

### Key Features
* 🐳 **Containerized Architecture:** Isolated Docker environments for App and Database (PostgreSQL).
* 📈 **Strategy Factory:** Plug-and-play strategy engine with **Vectorized Execution** for high performance (Currently supporting **EMA Crossover** & **RSI Mean Reversion**).
* 🧪 **Backtest Lab:** Realistic simulation engine with **Fee/Commission structure** (Fixed + Variable), Benchmark capabilities, and detailed metrics (ROI, Max Drawdown).
* 🛡️ **Risk First:** Built-in Risk Manager enforcing the 2% Rule and ATR-based volatility stops.
* 📊 **Interactive Dashboard:** Streamlit UI for portfolio monitoring, strategy configuration, system control, and log inspection.

---

## ⚙️ Configuration (`config/strategies.json`)

The system behavior is fully customizable via JSON, manageable directly from the **Control Panel**:

- **`active_strategy`**: Selects the logic to run in production (e.g., "RSI").
- **`risk_params`**: Controls capital exposure (Risk % per trade, Stop Loss ATR multiplier).
- **`fees_config`**: Simulates broker costs (Fixed fee + % per trade) for realistic backtests and net-profit calculation.
- **`strategies_params`**: Specific parameters for each algorithm (e.g., RSI Period, EMA Windows).

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

Detailed documentation is available in the **[GitHub Wiki](https://github.com/leoBitto/petunia/wiki)**.

* **[Strategy Playbook](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Strategy-Playbook):** Deep dive into EMA and RSI logic.
* **[Risk Management](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Risk-Management-Bible):** How position sizing and Fee calculation works.
* **[Architecture](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Architecture-%2526-Data-Flow):** System internals and data pipeline.
* **[Developer Guide](https://www.google.com/search?q=https://github.com/leoBitto/petunia/wiki/Developer-Guide):** Project structure and contribution guidelines.

---

## 🧭 Roadmap

### v1.x - Expansion & Testing (Completed)

| Status | Module | Description |
| --- | --- | --- |
| ✅ | **Core v1.0** | Stable Docker Architecture, Risk Manager |
| ✅ | **Strategies** | Implemented Trend Following (EMA) & Mean Reversion (RSI) Logic |
| ✅ | **Dynamic Config** | Allow Strategy & Fee selection via Frontend |
| ✅ | **Backtest Lab** | Vectorized Engine, Max Drawdown Metrics & Fee Adjustment |

### v2.0 - Cloud Native & DevOps (Next Up)

| Status | Module | Description |
| --- | --- | --- |
| 🔮 | **IaC** | Terraform for GCP Infrastructure provisioning |
| 🔮 | **Cloud Deploy** | Production deployment on GCP Compute Engine |
| 🔮 | **Secret Mgr** | Migration to Google Secret Manager (No more .env) |
| 🔮 | **Automation** | Systemd services & Auto-healing pipelines |

### v3.0 - Quantitative Scaling & Optimization

* **Grid Search Optimization:** Automated finding of best parameters (e.g., Best RSI period for Apple vs Tesla).
* **Universe Expansion:** Scaling data engine to handle 500+ tickers (S&P 500).
* **Deep Analytics:** Sharpe Ratio, Calmar Ratio, and Monte Carlo simulations.

### v4.0 - AI Agent & Alternative Data

* **Sentiment Analysis:** LLM-based analysis of financial news and social sentiment.
* **AI Oracle:** An autonomous agent that selects the best strategy based on current market regime.
* **Headless Mode:** Full autonomy with reduced UI dependency.

---

## 📄 License

Released under the **MIT License**.
© 2026 Leonardo Bitto
