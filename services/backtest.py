import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
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
    
    print(f"\n--- 🕵️ DEBUG START: {strategy_name} ---")
    
    # 1. CHECK DATI INPUT
    if not data_map:
        print("❌ ERRORE: data_map è vuoto!")
        return

    first_ticker = list(data_map.keys())[0]
    df_example = data_map[first_ticker]
    print(f"📊 Dati caricati per {len(data_map)} ticker.")
    print(f"📅 Esempio ({first_ticker}): {len(df_example)} righe.")
    print(f"   Min Date: {df_example['date'].min()} | Max Date: {df_example['date'].max()}")

    # 2. CALCOLO STRATEGIA
    try:
        strategy = get_strategy(strategy_name, **strategy_params)
        all_signals = strategy.compute(data_map)
    except Exception as e:
        print(f"❌ ERRORE Strategy Compute: {e}")
        return

    if all_signals.empty:
        print("⚠️ Nessun segnale generato (all_signals empty).")
        return

    # 3. DEBUG DATE SEGNALI
    all_signals['date'] = pd.to_datetime(all_signals['date'])
    print(f"🚦 Segnali Generati: {len(all_signals)} righe.")
    print(f"   Segnali Min Date: {all_signals['date'].min()}")
    print(f"   Segnali Max Date: {all_signals['date'].max()}")
    
    # Conta quanti segnali BUY/SELL ci sono
    counts = all_signals['signal'].value_counts()
    print(f"   Distribuzione: {counts.to_dict()}")

    # 4. DEBUG LOOP TEMPORALE
    all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
    # Conversione sicura per confronto
    all_dates_dt = [pd.to_datetime(d) for d in all_dates]
    
    start_date = datetime.now() - timedelta(days=days_history)
    print(f"⏳ Filtro Temporale: Cerco date successive a {start_date.date()}")
    
    sim_dates = [d for d in all_dates_dt if d >= pd.Timestamp(start_date)]
    
    print(f"🗓️ Giorni nel Loop di Simulazione: {len(sim_dates)}")
    if len(sim_dates) > 0:
        print(f"   Prima data sim: {sim_dates[0]} | Ultima: {sim_dates[-1]}")
    else:
        print("❌ ERRORE CRITICO: sim_dates è vuoto! Il backtest non girerà.")

    # 5. RISK MANAGER SETUP
    try:
        settings = SettingsManager()
        # Se risk_params arriva vuoto o None, usiamo il getter del manager
        if not risk_params:
            risk_params = settings.get_risk_params()

        pm = PortfolioManager()
        pm.update_cash(initial_capital)
        
        rm = RiskManager(
            risk_per_trade=risk_params.get("risk_per_trade", 0.02),
            stop_atr_multiplier=risk_params.get("stop_atr_multiplier", 2.0)
        )
    except Exception as e:
        print(f"❌ ERRORE Setup Manager: {e}")
        return

    equity_curve = []
    
    # 6. LOOP ESECUZIONE
    trades_count = 0
    for current_date in sim_dates:
        # Nota: current_date è già Timestamp qui
        
        # Mark-to-Market
        current_prices = {}
        for ticker, df in data_map.items():
            # Filtro data. Attenzione: df['date'] nel DB potrebbe essere stringa o object
            # Per sicurezza convertiamo al volo o assumiamo coerenza se fatto in load
            row = df[pd.to_datetime(df['date']) == current_date]
            if not row.empty:
                current_prices[ticker] = float(row.iloc[0]['close'])
        
        pm.update_market_prices(current_prices)
        
        # Filtro segnali
        daily_signals = all_signals[all_signals['date'] == current_date]
        
        # DEBUG SUI SEGNALI GIORNALIERI (Solo se ce ne sono)
        if not daily_signals.empty:
            relevant = daily_signals[daily_signals['signal'].isin(['BUY', 'SELL'])]
            if not relevant.empty:
                # Scommenta se vuoi vedere ogni segnale passare
                # print(f"   🧐 {current_date.date()}: Trovati {len(relevant)} segnali potenziali.")
                pass

        orders = rm.evaluate(
            daily_signals, 
            pm.get_total_equity(), 
            float(pm.df_cash.iloc[0]['cash']), 
            dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
        )
        
        for order in orders:
            pm.execute_order(order)
            if order['action'] == 'BUY':
                trades_count += 1

        equity_curve.append({
            "date": current_date,
            "equity": pm.get_total_equity()
        })

    print(f"🏁 Backtest Finito. Trades eseguiti: {trades_count}")
    print("--- DEBUG END ---\n")

    # Save Results (Codice originale)
    df_equity = pd.DataFrame(equity_curve)
    final_equity = df_equity.iloc[-1]['equity'] if not df_equity.empty else initial_capital
    
    config_dump = {
        "strategy": strategy_name,
        "params": strategy_params,
        "risk_params": risk_params,
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_trades": len(pm.df_trades[pm.df_trades['action']=='SELL'])
    }
    save_results(output_dir, strategy_name, df_equity, pm.df_trades, config_dump)

# --- API ENTRY POINT ---

def run_backtest_session(mode: str = "DEFAULT", 
                         override_strat_name: str = None, 
                         override_params: dict = None,
                         initial_capital: float = 10000.0,
                         years: int = 2) -> str:
    """
    Funzione principale (Orchestrator).
    Carica Configurazione e Dati UNA VOLTA sola, poi orchestra le esecuzioni.
    """
    settings = SettingsManager()
    db = DatabaseManager()
    
    # 1. Caricamento Parametri Rischio (GLOBAL)
    try:
        risk_params = settings.get_risk_params()
        logger.info(f"⚖️ Risk Config Loaded: {risk_params}")
    except Exception as e:
        logger.critical(f"Impossibile avviare backtest: {e}")
        return ""

    # 2. Preparazione Strategie da Eseguire
    strategies_to_run = [] 
    
    if mode == "ALL":
        # Modalità BATCH: Legge tutto dal JSON
        logger.info("📢 Modalità BATCH: Esecuzione di TUTTE le strategie.")
        all_configs = settings.load_config().get("strategies_params", {})
        for name, params in all_configs.items():
            if name in STRATEGY_MAP:
                strategies_to_run.append((name, params))
                
    elif mode == "SINGLE_OVERRIDE":
        # Modalità CUSTOM UI: Parametri passati esplicitamente
        if not override_strat_name or override_params is None:
            raise ValueError("Per SINGLE_OVERRIDE servono nome e params.")
        logger.info(f"🎯 Modalità CUSTOM UI: {override_strat_name} con params custom.")
        strategies_to_run.append((override_strat_name, override_params))
        
    else:
        # Modalità DEFAULT (CLI singola o JSON attivo)
        target = override_strat_name if override_strat_name else settings.get_active_strategy_name()
        logger.info(f"⚙️ Modalità STANDARD: {target} da Config JSON.")
        params = settings.get_strategy_params(target)
        strategies_to_run.append((target, params))

    if not strategies_to_run:
        logger.error("Nessuna strategia da eseguire.")
        return ""

    # 3. Data Fetching Centralizzato
    days = years * 365
    logger.info(f"📥 Fetching Data ({days} days)...")
    data_map = db.get_ohlc_all_tickers(days=days + 200)
    
    if not data_map:
        logger.error("Nessun dato nel DB per il backtest.")
        return ""

    # 4. Creazione Sessione
    base_dir = Path("data/backtests")
    session_dir = get_session_dir(base_dir)
    
    # 5. Loop Esecuzione (Passiamo risk_params!)
    for name, params in strategies_to_run:
        _execute_single_strategy(
            strategy_name=name, 
            strategy_params=params, 
            risk_params=risk_params,
            data_map=data_map, 
            output_dir=session_dir, 
            initial_capital=initial_capital, 
            days_history=days 
        )
        
    logger.info(f"✅ Sessione completata in: {session_dir}")
    return str(session_dir)

# --- CLI ENTRY POINT ---
def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    if arg == "ALL":
        run_backtest_session(mode="ALL")
    elif arg and arg in STRATEGY_MAP:
        run_backtest_session(mode="DEFAULT", override_strat_name=arg)
    else:
        run_backtest_session(mode="DEFAULT")

if __name__ == "__main__":
    main()