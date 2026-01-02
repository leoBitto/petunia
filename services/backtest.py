import pandas as pd
import numpy as np
import matplotlib
# Impostiamo il backend 'Agg' per generare grafici senza schermo (Headless/Docker)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import datetime, timedelta

# Import Core
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.risk_manager import RiskManager
from src.logger import get_logger

# Import Strategie
from src.strategy_RSI import StrategyRSI

logger = get_logger("Backtester")

def save_backtest_results(strategy_name: str, equity_df: pd.DataFrame, trades_df: pd.DataFrame, config: dict):
    """
    Salva i risultati in una struttura ordinata:
    data/backtests/<StrategyName>/<YYYY-MM-DD_HH-MM>/
    """
    # 1. Crea Path
    base_dir = Path("data/backtests")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base_dir / strategy_name / timestamp
    
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Salva CSV Dati
    equity_df.to_csv(run_dir / "equity_curve.csv", index=False)
    trades_df.to_csv(run_dir / "trades.csv", index=False)
    
    # 3. Salva Configurazione JSON
    with open(run_dir / "config.json", "w") as f:
        json.dump(config, f, indent=4, default=str)
        
    # 4. Genera e Salva Grafico (PNG)
    plt.figure(figsize=(10, 6))
    plt.plot(pd.to_datetime(equity_df['date']), equity_df['equity'], label='Equity', color='#4CAF50')
    plt.title(f"Equity Curve - {strategy_name}")
    plt.xlabel("Date")
    plt.ylabel("Capital (€)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.savefig(run_dir / "chart.png")
    plt.close()

    logger.info(f"✅ Risultati salvati in: {run_dir}")
    return str(run_dir)

def run_backtest(strategy_name: str = "RSI", 
                 initial_capital: float = 10000.0, 
                 days_history: int = 365*2,
                 strategy_params: dict = None):
    
    # Default params se vuoti
    if strategy_params is None:
        strategy_params = {}

    logger.info(f"🚀 Avvio Backtest: {strategy_name} | Params: {strategy_params}")
    
    # 1. SETUP
    db = DatabaseManager()
    pm = PortfolioManager()
    pm.update_cash(initial_capital)
    rm = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
    
    # Iniezione Parametri Dinamici nella Strategia
    if strategy_name == "RSI":
        # Usa i parametri passati o i default della classe
        strategy = StrategyRSI(
            rsi_period=strategy_params.get('rsi_period', 14),
            rsi_lower=strategy_params.get('rsi_lower', 30),
            rsi_upper=strategy_params.get('rsi_upper', 70),
            atr_period=strategy_params.get('atr_period', 14)
        )
    else:
        logger.error(f"Strategia {strategy_name} non implementata.")
        return

    # 2. DATI
    logger.info("📥 Caricamento dati storici...")
    data_map = db.get_ohlc_all_tickers(days=days_history + 100)
    
    if not data_map:
        logger.error("❌ Nessun dato trovato nel DB.")
        return

    # 3. SEGNALI
    logger.info("🧠 Calcolo segnali...")
    all_signals = strategy.compute(data_map)
    
    if all_signals.empty:
        logger.warning("⚠️ Nessun segnale generato.")
        return
    
    all_signals['date'] = pd.to_datetime(all_signals['date'])
    all_signals.sort_values('date', inplace=True)

    # 4. SIMULAZIONE
    logger.info("▶️ Simulazione temporale...")
    all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
    start_date = datetime.now() - timedelta(days=days_history)
    sim_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]

    equity_curve = []

    for current_date in sim_dates:
        # A. Mark-to-Market
        current_prices = {}
        for ticker, df in data_map.items():
            row = df[df['date'] == current_date]
            if not row.empty:
                current_prices[ticker] = row.iloc[0]['close']
        
        pm.update_market_prices(current_prices)
        
        # B. Risk & Execution
        daily_signals = all_signals[all_signals['date'] == current_date]
        
        pos_dict = dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
        equity = pm.get_total_equity()
        cash = float(pm.df_cash.iloc[0]['cash']) if not pm.df_cash.empty else 0.0
        
        orders = rm.evaluate(daily_signals, equity, cash, pos_dict)
        
        for order in orders:
            pm.execute_order(order)

        # C. Log Giornaliero
        equity_curve.append({
            "date": current_date,
            "equity": pm.get_total_equity(),
            "cash": pm.df_cash.iloc[0]['cash'] if not pm.df_cash.empty else 0.0
        })

    # 5. SALVATAGGIO
    df_equity = pd.DataFrame(equity_curve)
    df_trades = pm.df_trades
    
    final_config = {
        "strategy": strategy_name,
        "initial_capital": initial_capital,
        "days": days_history,
        "params": strategy_params,
        "final_equity": df_equity.iloc[-1]['equity'] if not df_equity.empty else initial_capital,
        "total_trades": len(df_trades[df_trades['action']=='SELL'])
    }
    
    save_backtest_results(strategy_name, df_equity, df_trades, final_config)

if __name__ == "__main__":
    # Esempio di esecuzione manuale
    run_backtest("RSI", strategy_params={"rsi_lower": 25, "rsi_upper": 75})