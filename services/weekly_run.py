import pandas as pd
from datetime import datetime

from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.yfinance_manager import YFinanceManager
from src.drive_manager import DriveManager
from src.risk_manager import RiskManager
from src.logger import get_logger
from src.strategy_RSI import StrategyRSI

logger = get_logger("WeeklyRun")

def main():
    logger.info("📅 Inizio Weekly Run (Strategy & Risk Analysis)...")
    
    # 1. INIT
    db = DatabaseManager()
    pm = PortfolioManager()
    yf = YFinanceManager()
    dm = DriveManager()
    
    # Config Strategia
    strategy = StrategyRSI(rsi_period=14, rsi_lower=30, rsi_upper=70)
    risk_manager = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
    
    # 2. LOAD STATE
    pm.load_from_db(db.load_portfolio())
    current_equity = pm.get_total_equity()
    logger.info(f"Equity Iniziale: {current_equity:.2f}")

    # 3. DATA FETCH (Universe + Portfolio)
    universe_tkr = dm.get_universe_tickers()
    portfolio_tkr = pm.df_portfolio["ticker"].tolist()
    all_tickers = list(set(universe_tkr + portfolio_tkr))
    
    logger.info(f"Aggiornamento dati per {len(all_tickers)} ticker...")
    new_data = yf.fetch_ohlc(all_tickers, days=5)
    db.upsert_ohlc(new_data)
    
    # 4. STRATEGY ENGINE
    logger.info("Recupero storico e calcolo strategia...")
    historical_data = db.get_ohlc_all_tickers(days=365)
    
    if not historical_data:
        logger.error("Nessun dato storico trovato.")
        return

    df_signals = strategy.compute(historical_data)
    
    # Filtro ultimo segnale (Venerdì)
    if df_signals.empty:
        latest_signals = pd.DataFrame()
    else:
        last_date = df_signals['date'].max()
        latest_signals = df_signals[df_signals['date'] == last_date]
        logger.info(f"Analisi segnali per data: {last_date}")

    # 5. RISK MANAGER
    pos_dict = dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
    available_cash = float(pm.df_cash.iloc[0]['cash']) if not pm.df_cash.empty else 0.0
    
    logger.info("Valutazione Rischio e Generazione Ordini...")
    orders = risk_manager.evaluate(
        signals_df=latest_signals,
        total_equity=current_equity,
        available_cash=available_cash,
        current_positions=pos_dict
    )
    
    # 6. OUTPUT -> GOOGLE SHEETS
    if orders:
        logger.info(f"✅ Generati {len(orders)} ordini operativi.")
        for o in orders:
            logger.info(f"   -> {o['action']} {o['ticker']} Qty:{o['quantity']} @ {o['price']}")
    else:
        logger.info("😴 Nessun ordine generato.")

    # SALVATAGGIO SUL CLOUD
    # Questo sovrascrive il tab "Orders" nel tuo Report Sheet
    dm.save_pending_orders(orders)
    
    logger.info("✅ Weekly Run completata. Ordini aggiornati su Drive.")

if __name__ == "__main__":
    main()