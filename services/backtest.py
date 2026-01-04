import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Headless mode
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# Core Imports
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.risk_manager import RiskManager
from src.settings_manager import SettingsManager
from src.logger import get_logger

# Factory
from src.strategies import get_strategy, STRATEGY_MAP

logger = get_logger("Backtester")

def get_session_dir(base_path: Path) -> Path:
    """
    Crea una directory unica per la sessione corrente.
    Format: data/backtests/YYYY-MM-DD_HH-MM[_n]
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    session_dir = base_path / timestamp
    
    # Gestione collisioni: aggiunge _1, _2, etc. se esiste già
    counter = 1
    original_path = session_dir
    while session_dir.exists():
        session_dir = base_path / f"{timestamp}_{counter}"
        counter += 1
    
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def save_results(output_dir: Path, strategy_name: str, equity_df: pd.DataFrame, trades_df: pd.DataFrame, config: dict):
    """
    Salva i risultati dentro la cartella della sessione, in una sottocartella per strategia.
    Path: session_dir/StrategyName/
    """
    strat_dir = output_dir / strategy_name
    strat_dir.mkdir(exist_ok=True)
    
    # CSV
    equity_df.to_csv(strat_dir / "equity_curve.csv", index=False)
    trades_df.to_csv(strat_dir / "trades.csv", index=False)
    
    # JSON Config
    with open(strat_dir / "config.json", "w") as f:
        json.dump(config, f, indent=4, default=str)
        
    # Chart
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

def run_single_backtest(strategy_name: str, 
                        strategy_params: dict,
                        data_map: Dict[str, pd.DataFrame],
                        output_dir: Path,
                        initial_capital: float = 10000.0,
                        days_history: int = 365):
    """
    Esegue il backtest per una singola strategia usando dati PRE-CARICATI.
    """
    logger.info(f"🚀 Avvio Backtest Strategia: {strategy_name}")
    
    # 1. SETUP AMBIENTE ISOLATO (Portfolio effimero)
    try:
        pm = PortfolioManager()
        pm.update_cash(initial_capital)
        rm = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
        
        # Factory Istanziazione
        strategy = get_strategy(strategy_name, **strategy_params)
    except Exception as e:
        logger.error(f"❌ Errore setup strategia {strategy_name}: {e}")
        return

    # 2. CALCOLO SEGNALI
    logger.info(f"   Analisi indicatori per {strategy_name}...")
    try:
        all_signals = strategy.compute(data_map)
    except Exception as e:
        logger.error(f"❌ Errore durante compute() di {strategy_name}: {e}")
        return
    
    if all_signals.empty:
        logger.warning(f"⚠️ {strategy_name}: Nessun segnale generato.")
        return # Salviamo comunque config vuota? Per ora usciamo.

    all_signals['date'] = pd.to_datetime(all_signals['date'])
    all_signals.sort_values('date', inplace=True)

    # 3. SIMULAZIONE TIME-LOOP
    # Filtriamo le date per la simulazione
    all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
    start_date = datetime.now() - timedelta(days=days_history)
    sim_dates = [d for d in all_dates if pd.to_datetime(d) >= pd.Timestamp(start_date)]

    equity_curve = []

    for current_date in sim_dates:
        current_date = pd.Timestamp(current_date)
        
        # A. Mark-to-Market
        current_prices = {}
        for ticker, df in data_map.items():
            row = df[df['date'] == current_date]
            if not row.empty:
                current_prices[ticker] = float(row.iloc[0]['close'])
        
        pm.update_market_prices(current_prices)
        
        # B. Risk & Execution
        daily_signals = all_signals[all_signals['date'] == current_date]
        pos_dict = dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
        equity = pm.get_total_equity()
        cash = float(pm.df_cash.iloc[0]['cash']) if not pm.df_cash.empty else 0.0
        
        orders = rm.evaluate(daily_signals, equity, cash, pos_dict)
        
        for order in orders:
            pm.execute_order(order)

        # C. Tracking
        equity_curve.append({
            "date": current_date,
            "equity": pm.get_total_equity()
        })

    # 4. REPORTING
    df_equity = pd.DataFrame(equity_curve)
    final_equity = df_equity.iloc[-1]['equity'] if not df_equity.empty else initial_capital
    pnl = final_equity - initial_capital
    
    logger.info(f"🏁 {strategy_name} Terminata. P&L: {pnl:+.2f} €")
    
    config_dump = {
        "strategy": strategy_name,
        "params": strategy_params,
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "pnl": pnl,
        "trades_count": len(pm.df_trades[pm.df_trades['action']=='SELL'])
    }
    
    save_results(output_dir, strategy_name, df_equity, pm.df_trades, config_dump)

def main():
    settings = SettingsManager()
    db = DatabaseManager()
    
    # 1. Configurazione Run
    target_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    strategies_to_run = [] # Lista di tuple (Nome, Params)
    
    if target_arg == "ALL":
        # Modalità BATCH: Prende tutte le strategie configurate nel JSON
        logger.info("📢 Modalità BATCH: Esecuzione di TUTTE le strategie.")
        all_configs = settings.load_config().get("strategies_params", {})
        
        # Filtriamo solo quelle che hanno anche una classe implementata nel Factory
        for name, params in all_configs.items():
            if name in STRATEGY_MAP:
                strategies_to_run.append((name, params))
            else:
                logger.warning(f"Strategia '{name}' presente nel JSON ma non nel Factory. Saltata.")
                
    elif target_arg and target_arg in STRATEGY_MAP:
        # Modalità Override Singolo
        logger.info(f"🎯 Modalità SINGLE: Esecuzione forzata di {target_arg}")
        params = settings.get_strategy_params(target_arg)
        strategies_to_run.append((target_arg, params))
        
    else:
        # Default: Usa la strategia attiva
        active = settings.get_active_strategy_name()
        logger.info(f"⚙️  Modalità DEFAULT: Esecuzione strategia attiva ({active})")
        params = settings.get_strategy_params(active)
        strategies_to_run.append((active, params))

    if not strategies_to_run:
        logger.error("Nessuna strategia valida da eseguire.")
        return

    # 2. Data Fetching (UNA VOLTA PER TUTTI)
    days_history = 365
    logger.info(f"📥 Caricamento dati storici centralizzato ({days_history} giorni)...")
    data_map = db.get_ohlc_all_tickers(days=days_history + 200) # Buffer per indicatori
    
    if not data_map:
        logger.error("❌ Dati insufficienti nel DB.")
        return

    # 3. Creazione Cartella Sessione
    base_dir = Path("data/backtests")
    session_dir = get_session_dir(base_dir)
    logger.info(f"📂 Cartella Sessione: {session_dir}")

    # 4. Loop di Esecuzione
    logger.info(f"🔥 Avvio benchmark su {len(strategies_to_run)} strategie...")
    
    for name, params in strategies_to_run:
        print(f"\n--- {name} START ---")
        run_single_backtest(
            strategy_name=name,
            strategy_params=params,
            data_map=data_map, # Passiamo i dati in memoria
            output_dir=session_dir,
            initial_capital=10000.0,
            days_history=days_history
        )
        print(f"--- {name} END ---\n")

    logger.info("✅ Sessione di Backtest completata.")

if __name__ == "__main__":
    main()