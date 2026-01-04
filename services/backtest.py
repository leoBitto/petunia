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

# --- HELPER FUNCTIONS (Logica Core) ---

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
                             data_map: Dict[str, pd.DataFrame],
                             output_dir: Path,
                             initial_capital: float,
                             days_history: int):
    """
    Funzione interna: Esegue logica di backtest per una strategia già configurata.
    """
    logger.info(f"🚀 Running: {strategy_name} | Params: {strategy_params}")
    
    try:
        pm = PortfolioManager()
        pm.update_cash(initial_capital)
        rm = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
        strategy = get_strategy(strategy_name, **strategy_params)
        
        # Compute Signals
        all_signals = strategy.compute(data_map)
        
        if all_signals.empty:
            logger.warning(f"⚠️ {strategy_name}: Nessun segnale.")
            # Salviamo comunque un report vuoto per tracciabilità
            save_results(output_dir, strategy_name, pd.DataFrame(), pd.DataFrame(), {"error": "No signals"})
            return

        all_signals['date'] = pd.to_datetime(all_signals['date'])
        all_signals.sort_values('date', inplace=True)

        # Simulation Loop
        all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
        start_date = datetime.now() - timedelta(days=days_history)
        sim_dates = [d for d in all_dates if pd.to_datetime(d) >= pd.Timestamp(start_date)]

        equity_curve = []

        for current_date in sim_dates:
            current_date = pd.Timestamp(current_date)
            
            # Mark-to-Market
            current_prices = {}
            for ticker, df in data_map.items():
                row = df[df['date'] == current_date]
                if not row.empty:
                    current_prices[ticker] = float(row.iloc[0]['close'])
            
            pm.update_market_prices(current_prices)
            
            # Risk & Exec
            daily_signals = all_signals[all_signals['date'] == current_date]
            orders = rm.evaluate(
                daily_signals, 
                pm.get_total_equity(), 
                float(pm.df_cash.iloc[0]['cash']), 
                dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
            )
            
            for order in orders:
                pm.execute_order(order)

            equity_curve.append({
                "date": current_date,
                "equity": pm.get_total_equity()
            })

        # Save
        df_equity = pd.DataFrame(equity_curve)
        final_equity = df_equity.iloc[-1]['equity'] if not df_equity.empty else initial_capital
        
        config_dump = {
            "strategy": strategy_name,
            "params": strategy_params,
            "initial_capital": initial_capital,
            "final_equity": final_equity,
            "total_trades": len(pm.df_trades[pm.df_trades['action']=='SELL'])
        }
        save_results(output_dir, strategy_name, df_equity, pm.df_trades, config_dump)

    except Exception as e:
        logger.error(f"❌ Errore in _execute_single_strategy ({strategy_name}): {e}")

# --- API ENTRY POINT (Per Dashboard & CLI) ---

def run_backtest_session(mode: str = "DEFAULT", 
                         override_strat_name: str = None, 
                         override_params: dict = None,
                         initial_capital: float = 10000.0,
                         years: int = 2) -> str:
    """
    Funzione principale chiamata dalla Dashboard o dalla CLI.
    Gestisce il Data Fetching una volta sola e orchestra le strategie.
    
    Returns:
        str: Il path della cartella di sessione creata.
    """
    settings = SettingsManager()
    db = DatabaseManager()
    
    # 1. Preparazione Configutazioni da Eseguire
    strategies_to_run = [] # Lista di tuple (Nome, Params)
    
    if mode == "ALL":
        # Modalità BENCHMARK: Prende tutto dal JSON
        logger.info("📢 Modalità BATCH: Esecuzione di TUTTE le strategie.")
        all_configs = settings.load_config().get("strategies_params", {})
        for name, params in all_configs.items():
            if name in STRATEGY_MAP:
                strategies_to_run.append((name, params))
                
    elif mode == "SINGLE_OVERRIDE":
        # Modalità DASHBOARD CUSTOM: Parametri passati esplicitamente
        if not override_strat_name or override_params is None:
            raise ValueError("Per SINGLE_OVERRIDE servono nome e params.")
        logger.info(f"🎯 Modalità CUSTOM UI: {override_strat_name} con params custom.")
        strategies_to_run.append((override_strat_name, override_params))
        
    else:
        # CLI DEFAULT / SINGLE ARGS: Logica precedente
        target = override_strat_name if override_strat_name else settings.get_active_strategy_name()
        logger.info(f"⚙️ Modalità STANDARD: {target} da Config JSON.")
        params = settings.get_strategy_params(target)
        strategies_to_run.append((target, params))

    if not strategies_to_run:
        logger.error("Nessuna strategia da eseguire.")
        return ""

    # 2. Data Fetching Centralizzato
    days = years * 365
    logger.info(f"📥 Fetching Data ({days} days)...")
    data_map = db.get_ohlc_all_tickers(days=days + 200)
    
    if not data_map:
        raise RuntimeError("Nessun dato nel DB per il backtest.")

    # 3. Creazione Sessione
    base_dir = Path("data/backtests")
    session_dir = get_session_dir(base_dir)
    
    # 4. Loop Esecuzione
    for name, params in strategies_to_run:
        _execute_single_strategy(name, params, data_map, session_dir, initial_capital, days)
        
    logger.info(f"✅ Sessione completata in: {session_dir}")
    return str(session_dir)

# --- CLI ENTRY POINT ---
def main():
    # Parsing argomenti CLI semplificato per uso legacy/script
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    if arg == "ALL":
        run_backtest_session(mode="ALL")
    elif arg and arg in STRATEGY_MAP:
        run_backtest_session(mode="DEFAULT", override_strat_name=arg)
    else:
        run_backtest_session(mode="DEFAULT")

if __name__ == "__main__":
    main()