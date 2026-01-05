import pandas as pd
from datetime import datetime
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.risk_manager import RiskManager
from src.settings_manager import SettingsManager
from src.strategies import get_strategy
from src.logger import get_logger

logger = get_logger("WeeklyRun")

def main():
    logger.info("🚀 Avvio Weekly Run (Strategia + Esecuzione)...")
    
    # 1. Setup Manager
    db = DatabaseManager()
    settings = SettingsManager()
    pm = PortfolioManager()
    
    # Carichiamo config rischio e strategia
    try:
        active_strat_name = settings.get_active_strategy_name()
        strat_params = settings.get_strategy_params(active_strat_name)
        risk_params = settings.get_risk_params()
        
        # Risk Manager inizializzato coi parametri JSON
        rm = RiskManager(
            risk_per_trade=risk_params["risk_per_trade"],
            stop_atr_multiplier=risk_params["stop_atr_multiplier"]
        )
        
        logger.info(f"⚙️ Config: {active_strat_name} | Risk: {risk_params['risk_per_trade']*100}%")
        
    except Exception as e:
        logger.critical(f"❌ Errore Configurazione: {e}")
        return

    # 2. Fetch Dati (Serve storico sufficiente per gli indicatori!)
    # Scarichiamo es. 365 giorni per essere sicuri che EMA200 funzioni
    logger.info("📥 Caricamento dati storici dal DB...")
    data_map = db.get_ohlc_all_tickers(days=365)
    
    if not data_map:
        logger.warning("⚠️ Nessun dato sufficiente per l'analisi.")
        return

    # 3. Calcolo Segnali (VETTORIALE - Restituisce tutto lo storico)
    strategy = get_strategy(active_strat_name, **strat_params)
    all_signals = strategy.compute(data_map)
    
    if all_signals.empty:
        logger.info("💤 Nessun segnale generato dalla strategia.")
        return

    # ------------------------------------------------------------------
    # 4. FILTRO "SOLO OGGI" 
    # ------------------------------------------------------------------
    # Troviamo la data più recente presente nei segnali
    # (Attenzione: Potrebbe essere Venerdì scorso se è Lunedì mattina e non abbiamo scaricato)
    latest_date = all_signals['date'].max()
    
    logger.info(f"📆 Filtraggio segnali per l'ultima data disponibile: {latest_date}")
    
    # Prendiamo solo i segnali dell'ultimo giorno disponibile
    latest_signals = all_signals[all_signals['date'] == latest_date].copy()
    
    if latest_signals.empty:
        logger.warning("⚠️ Strano: Nessun segnale per l'ultima data.")
        return

    # Logghiamo cosa abbiamo trovato oggi
    buy_signals = latest_signals[latest_signals['signal'] == 'BUY']
    sell_signals = latest_signals[latest_signals['signal'] == 'SELL']
    logger.info(f"🔎 Analisi Oggi: {len(buy_signals)} BUY, {len(sell_signals)} SELL su {len(latest_signals)} ticker.")

    # 5. Esecuzione (Mark-to-Market & Risk Management)
    # Aggiorniamo i prezzi del portafoglio all'ultimo prezzo noto
    current_prices = dict(zip(latest_signals['ticker'], latest_signals['price']))
    pm.update_market_prices(current_prices)

    # Risk Manager valuta SOLO i segnali filtrati
    orders = rm.evaluate(
        latest_signals, 
        pm.get_total_equity(), 
        float(pm.df_cash.iloc[0]['cash']), 
        dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
    )
    
    # 6. Invio Ordini
    if not orders:
        logger.info("✅ Nessun ordine da eseguire oggi.")
    else:
        for order in orders:
            logger.info(f"🔔 ESECUZIONE: {order['action']} {order['quantity']} {order['ticker']}")
            pm.execute_order(order)
            
    logger.info("🏁 Weekly Run Completata.")

if __name__ == "__main__":
    main()