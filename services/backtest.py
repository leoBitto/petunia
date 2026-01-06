import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Core Imports
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.risk_manager import RiskManager
from src.settings_manager import SettingsManager
from src.logger import get_logger
from src.strategies import get_strategy, STRATEGY_MAP

logger = get_logger("Backtester")

# --- HELPER FUNCTIONS ---

def get_session_dir(base_path: Path) -> Path:
    """Crea directory unica per la sessione."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    session_dir = base_path / timestamp
    counter = 1
    while session_dir.exists():
        session_dir = base_path / f"{timestamp}_{counter}"
        counter += 1
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def calculate_max_drawdown(equity_series: pd.Series) -> float:
    """Calcola il Max Drawdown in percentuale."""
    if equity_series.empty: return 0.0
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    return drawdown.min() * 100

def save_results(output_dir: Path, strategy_name: str, equity_df: pd.DataFrame, trades_df: pd.DataFrame, config: dict):
    """Salva i risultati su disco."""
    strat_dir = output_dir / strategy_name
    strat_dir.mkdir(exist_ok=True)
    
    equity_df.to_csv(strat_dir / "equity_curve.csv", index=False)
    trades_df.to_csv(strat_dir / "trades.csv", index=False)
    
    with open(strat_dir / "config.json", "w") as f:
        json.dump(config, f, indent=4, default=str)
        
    if not equity_df.empty:
        plt.figure(figsize=(10, 6))
        plt.plot(pd.to_datetime(equity_df['date']), equity_df['equity'], label='Equity', color='#4CAF50')
        plt.title(f"Equity Curve - {strategy_name}")
        plt.xlabel("Date")
        plt.ylabel("Capital (€)")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.savefig(strat_dir / "chart.png")
        plt.close()
    
    logger.info(f"💾 Risultati salvati in: {strat_dir}")

def _execute_single_strategy(strategy_name: str, 
                             strategy_params: dict,
                             risk_params: dict,
                             data_map: Dict[str, pd.DataFrame],
                             output_dir: Path,
                             initial_capital: float,
                             days_history: int):
    
    logger.info(f"--- 🚀 RUN: {strategy_name} (Weekly Execution / Daily Monitoring) ---")
    
    # 1. Caricamento Commissioni
    try:
        settings = SettingsManager()
        fees_conf = settings.get_fees_config()
        fee_fixed = fees_conf.get("fixed_euro", 0.0)
        fee_pct = fees_conf.get("percentage", 0.0)
        logger.info(f"💰 Cost Structure: €{fee_fixed} + {fee_pct*100}% per trade.")
    except:
        fee_fixed, fee_pct = 0.0, 0.0

    # 2. Setup Managers
    try:
        pm = PortfolioManager()
        pm.update_cash(initial_capital)
        rm = RiskManager(
            risk_per_trade=risk_params.get("risk_per_trade", 0.02),
            stop_atr_multiplier=risk_params.get("stop_atr_multiplier", 2.0)
        )
        strategy = get_strategy(strategy_name, **strategy_params)
    except Exception as e:
        logger.error(f"❌ Setup Error: {e}")
        return

    # 3. Calcolo Segnali (Vengono calcolati su tutto lo storico in una volta sola)
    try:
        all_signals = strategy.compute(data_map)
    except Exception as e:
        logger.error(f"❌ Strategy Compute Error: {e}")
        return

    if not all_signals.empty:
        all_signals['date'] = pd.to_datetime(all_signals['date'])
        all_signals.sort_values('date', inplace=True)

    # 4. Setup Loop Temporale
    all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
    start_date = datetime.now() - timedelta(days=days_history)
    sim_dates = [d for d in all_dates if pd.to_datetime(d) >= pd.Timestamp(start_date)]
    
    equity_curve = []
    trades_count = 0
    total_fees_paid = 0.0
    
    # Lista per gli ordini decisi venerdì ed eseguiti lunedì
    pending_entry_orders = []

    # 5. Loop Esecuzione (GIORNALIERO)
    for current_date in sim_dates:
        current_date = pd.Timestamp(current_date)
        is_friday = current_date.dayofweek == 4  # 0=Mon, 4=Fri

        # Recuperiamo i dati di oggi (Open, High, Low, Close)
        todays_prices = {}
        for ticker, df in data_map.items():
            row = df[pd.to_datetime(df['date']) == current_date]
            if not row.empty:
                todays_prices[ticker] = {
                    'open': float(row.iloc[0]['open']),
                    'high': float(row.iloc[0]['high']),
                    'low': float(row.iloc[0]['low']),
                    'close': float(row.iloc[0]['close'])
                }

        # Aggiorniamo il valore del portfolio con i prezzi di chiusura di oggi (Mark-to-Market)
        current_closes = {t: data['close'] for t, data in todays_prices.items()}
        pm.update_market_prices(current_closes)

        # ---------------------------------------------------------------------
        # FASE A: ESECUZIONE ORDINI PENDENTI (Lunedì mattina / Next Open)
        # ---------------------------------------------------------------------
        # Se ci sono ordini nella "busta" (decisi venerdì scorso), li eseguiamo all'OPEN di oggi
        if pending_entry_orders:
            executed_orders = []
            for order in pending_entry_orders:
                ticker = order['ticker']
                
                # Se il titolo è quotato oggi
                if ticker in todays_prices:
                    # SIMULAZIONE SLIPPAGE/GAP: Eseguiamo al prezzo di APERTURA reale
                    execution_price = todays_prices[ticker]['open']
                    order['price'] = execution_price 
                    
                    # Tentativo di esecuzione (il PM controlla se ho cash sufficiente)
                    if pm.execute_order(order):
                        # Calcolo fee
                        trade_val = execution_price * order['quantity']
                        commission = fee_fixed + (trade_val * fee_pct)
                        pm.update_cash(float(pm.df_cash.iloc[0]['cash']) - commission)
                        total_fees_paid += commission
                        if order['action'] == 'BUY': trades_count += 1
                        
            # Svuotiamo la lista ordini pendenti una volta provati tutti
            pending_entry_orders = []

        # ---------------------------------------------------------------------
        # FASE B: SORVEGLIANZA GIORNALIERA (Stop Loss & Take Profit)
        # ---------------------------------------------------------------------
        # Controlliamo se i massimi/minimi DI OGGI hanno toccato gli stop delle posizioni aperte.
        # Questo simula gli ordini GTC sul broker.
        
        # Estraiamo High e Low per il Risk Manager
        todays_highs = {t: data['high'] for t, data in todays_prices.items()}
        todays_lows = {t: data['low'] for t, data in todays_prices.items()}

        # Chiediamo al RM di controllare SOLO le posizioni esistenti
        # (Assicurati che RiskManager abbia il metodo check_intraday_stops)
        exit_orders = rm.check_intraday_stops(
            pm.get_positions_snapshot(), # Assumi che ritorni un dict {ticker: position_obj/dict}
            todays_highs, 
            todays_lows
        )
        
        for order in exit_orders:
            # Eseguiamo l'uscita
            if pm.execute_order(order):
                # Fee su uscita
                trade_val = order['price'] * order['quantity']
                commission = fee_fixed + (trade_val * fee_pct)
                pm.update_cash(float(pm.df_cash.iloc[0]['cash']) - commission)
                total_fees_paid += commission


        # ---------------------------------------------------------------------
        # FASE C: STRATEGIA SETTIMANALE (Solo Venerdì)
        # ---------------------------------------------------------------------
        # Se oggi è Venerdì, guardiamo i grafici e prepariamo gli ordini per Lunedì
        if is_friday and not all_signals.empty:
            daily_signals = all_signals[all_signals['date'] == current_date]
            
            if not daily_signals.empty:
                # Usiamo evaluate per calcolare size e stop, MA NON ESEGUIAMO
                # Notare: passiamo il cash attuale, ma gli ordini verranno eseguiti lunedì
                # con il cash che avremo lunedì (potenzialmente diverso se ci sono costi).
                # Per semplicità, assumiamo che il cash di venerdì sera sia una buona stima.
                new_orders = rm.evaluate(
                    daily_signals, 
                    pm.get_total_equity(), 
                    float(pm.df_cash.iloc[0]['cash']), 
                    pm.get_positions_counts()
                )
                
                # Mettiamo gli ordini in coda per la prossima apertura (Lunedì)
                pending_entry_orders.extend(new_orders)

        # ---------------------------------------------------------------------
        # Tracking & Logging
        # ---------------------------------------------------------------------
        equity_curve.append({
            "date": current_date,
            "equity": pm.get_total_equity()
        })

    logger.info(f"🏁 Finito. Trades: {trades_count} | Fees Totali: €{total_fees_paid:.2f}")

    # 6. Reporting Finale
    df_equity = pd.DataFrame(equity_curve)
    final_equity = df_equity.iloc[-1]['equity'] if not df_equity.empty else initial_capital
    max_dd = calculate_max_drawdown(df_equity['equity']) if not df_equity.empty else 0.0
    roi = ((final_equity - initial_capital) / initial_capital) * 100
    
    config_dump = {
        "strategy": strategy_name,
        "params": strategy_params,
        "risk_params": risk_params,
        "fees_config": fees_conf,
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "metrics": {
            "total_trades": len(pm.df_trades[pm.df_trades['action']=='SELL']),
            "total_fees": round(total_fees_paid, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "roi_pct": round(roi, 2)
        }
    }
    save_results(output_dir, strategy_name, df_equity, pm.df_trades, config_dump)

# --- API ENTRY POINT ---

def run_backtest_session(mode: str = "DEFAULT", 
                         override_strat_name: str = None, 
                         override_params: dict = None,
                         initial_capital: float = 10000.0,
                         years: int = 2) -> str:
    settings = SettingsManager()
    db = DatabaseManager()
    
    try:
        risk_params = settings.get_risk_params()
    except Exception as e:
        logger.critical(f"Config Error: {e}")
        return ""

    strategies_to_run = [] 
    if mode == "ALL":
        all_configs = settings.load_config().get("strategies_params", {})
        for name, params in all_configs.items():
            if name in STRATEGY_MAP:
                strategies_to_run.append((name, params))
    elif mode == "SINGLE_OVERRIDE":
        strategies_to_run.append((override_strat_name, override_params))
    else:
        target = override_strat_name if override_strat_name else settings.get_active_strategy_name()
        params = settings.get_strategy_params(target)
        strategies_to_run.append((target, params))

    days = years * 365
    logger.info(f"📥 Fetching Data ({days} days)...")
    data_map = db.get_ohlc_all_tickers(days=days + 200)
    
    if not data_map:
        logger.error("No Data.")
        return ""

    base_dir = Path("data/backtests")
    session_dir = get_session_dir(base_dir)
    
    for name, params in strategies_to_run:
        _execute_single_strategy(name, params, risk_params, data_map, session_dir, initial_capital, days)
        
    return str(session_dir)

# --- CLI ENTRY POINT ---
def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "ALL": run_backtest_session(mode="ALL")
    elif arg and arg in STRATEGY_MAP: run_backtest_session(mode="DEFAULT", override_strat_name=arg)
    else: run_backtest_session(mode="DEFAULT")

if __name__ == "__main__":
    main()