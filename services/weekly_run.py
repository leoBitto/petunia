import pandas as pd
from datetime import datetime

from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.yfinance_manager import YFinanceManager
from src.drive_manager import DriveManager
from src.risk_manager import RiskManager
from src.settings_manager import SettingsManager
from src.logger import get_logger

# Importiamo SOLO il Factory Method, non le classi specifiche
from src.strategies import get_strategy 

logger = get_logger("WeeklyRun")

def main():
    logger.info("📅 Inizio Weekly Run (Strategy & Risk Analysis)...")
    
    # 1. INIT MANAGERS
    try:
        db = DatabaseManager()
        pm = PortfolioManager()
        yf = YFinanceManager()
        dm = DriveManager()
        settings = SettingsManager() # Carica config/strategies.json
    except Exception as e:
        logger.critical(f"Errore inizializzazione manager: {e}")
        return
    
    # 2. CONFIGURAZIONE DINAMICA STRATEGIA
    try:
        # Leggiamo dal JSON quale strategia usare
        active_strat_name = settings.get_active_strategy_name()
        strat_params = settings.get_strategy_params(active_strat_name)
        
        logger.info(f"⚙️  Strategia Attiva: {active_strat_name}")
        logger.info(f"🔧 Parametri: {strat_params}")
        
        # FACTORY PATTERN: Istanziamo la classe corretta al volo
        strategy = get_strategy(active_strat_name, **strat_params)
        
    except Exception as e:
        logger.critical(f"Errore caricamento strategia da config: {e}")
        return

    # Inizializziamo Risk Manager (NB: potremmo parametrizzare anche questo in futuro)
    risk_manager = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
    
    # 3. LOAD STATE
    try:
        pm.load_from_db(db.load_portfolio())
        current_equity = pm.get_total_equity()
        logger.info(f"💰 Equity Iniziale: {current_equity:.2f} €")
    except Exception as e:
        logger.error(f"Errore caricamento portfolio: {e}")
        return

    # 4. DATA FETCH (Universe + Portfolio)
    universe_tkr = dm.get_universe_tickers()
    portfolio_tkr = pm.df_portfolio["ticker"].tolist()
    all_tickers = list(set(universe_tkr + portfolio_tkr))
    
    if not all_tickers:
        logger.warning("Nessun ticker da analizzare.")
        return

    logger.info(f"Aggiornamento dati per {len(all_tickers)} ticker...")
    # Scarichiamo dati recenti per aggiornare il DB
    new_data = yf.fetch_ohlc(all_tickers, days=5)
    db.upsert_ohlc(new_data)
    
    # 5. STRATEGY ENGINE
    # Per la strategia servono dati storici profondi (es. EMA 200 richiede >200 giorni)
    logger.info("Recupero storico e calcolo segnali...")
    historical_data = db.get_ohlc_all_tickers(days=365)
    
    if not historical_data:
        logger.error("Nessun dato storico trovato nel DB.")
        return

    # Calcolo della strategia dinamica
    df_signals = strategy.compute(historical_data)
    
    # Filtro ultimo segnale (Venerdì/Oggi)
    if df_signals.empty:
        logger.info("Nessun segnale generato dalla strategia.")
        latest_signals = pd.DataFrame()
    else:
        last_date = df_signals['date'].max()
        latest_signals = df_signals[df_signals['date'] == last_date]
        logger.info(f"Analisi segnali per data: {last_date.date()}")

    # 6. RISK MANAGER & ORDER GENERATION
    pos_dict = dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
    available_cash = float(pm.df_cash.iloc[0]['cash']) if not pm.df_cash.empty else 0.0
    
    logger.info("Valutazione Rischio...")
    orders = risk_manager.evaluate(
        signals_df=latest_signals,
        total_equity=current_equity,
        available_cash=available_cash,
        current_positions=pos_dict
    )
    
    # 7. OUTPUT -> GOOGLE SHEETS
    if orders:
        logger.info(f"✅ Generati {len(orders)} ordini operativi.")
        for o in orders:
            logger.info(f"   -> {o['action']} {o['ticker']} Qty:{o['quantity']} @ {o['price']:.2f}")
    else:
        logger.info("😴 Nessun ordine generato (Risk Manager o Nessun Segnale).")

    # Questo sovrascrive il tab "Orders" nel tuo Report Sheet
    dm.save_pending_orders(orders)
    
    logger.info("✅ Weekly Run completata. Ordini aggiornati su Drive.")

if __name__ == "__main__":
    main()