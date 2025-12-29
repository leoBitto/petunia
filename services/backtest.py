import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import Core
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.risk_manager import RiskManager
from src.logger import get_logger

# Import Strategie (Espandibile)
from src.strategy_RSI import StrategyRSI
# from src.strategy_MSI import StrategyMSI 

logger = get_logger("Backtester")

def analyze_trades(trades_df: pd.DataFrame, initial_capital: float, final_equity: float):
    """Calcola metriche avanzate basandosi sullo storico dei trade."""
    if trades_df.empty:
        logger.warning("Nessun trade eseguito.")
        return

    # Filtriamo solo le vendite per calcolare il P&L realizzato
    # (Per semplicità, assumiamo che ogni SELL chiuda una operazione)
    # Una analisi più complessa richiederebbe di macciare BUY e SELL.
    # Qui facciamo una stima basata sull'Equity finale vs Iniziale per il totale,
    # e contiamo le operazioni per le statistiche di frequenza.
    
    total_trades = len(trades_df[trades_df['action'] == 'SELL'])
    buys = len(trades_df[trades_df['action'] == 'BUY'])
    
    print("\n" + "="*40)
    print(f"📊 REPORT BACKTEST")
    print("="*40)
    print(f"Capitale Iniziale:   € {initial_capital:,.2f}")
    print(f"Equity Finale:       € {final_equity:,.2f}")
    
    total_return = (final_equity - initial_capital)
    return_pct = (total_return / initial_capital) * 100
    print(f"Profitto Netto:      € {total_return:,.2f} ({return_pct:+.2f}%)")
    print("-" * 40)
    print(f"Totale Operazioni:   {buys} BUY / {total_trades} SELL")
    
    # Qui servirebbe una logica P&L per trade specifica per calcolare WinRate.
    # Dato che il PortfolioManager non salva il P&L del singolo trade nello storico,
    # per ora ci limitiamo all'Equity Curve. 
    # (TODO per il futuro: aggiungere colonna 'realized_pnl' in df_trades su SELL)

def run_backtest(strategy_name: str = "RSI", 
                 initial_capital: float = 10000.0, 
                 days_history: int = 365*2):
    
    logger.info(f"🚀 Avvio Backtest: {strategy_name}, Cap: {initial_capital}, Giorni: {days_history}")
    
    # 1. SETUP
    db = DatabaseManager()
    
    # Portfolio Virtuale (NON connesso al DB per il load)
    pm = PortfolioManager()
    pm.update_cash(initial_capital)
    
    # Risk Manager
    rm = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
    
    # Strategia
    if strategy_name == "RSI":
        strategy = StrategyRSI(rsi_lower=30, rsi_upper=70) # Parametri standard
    else:
        logger.error(f"Strategia {strategy_name} non implementata.")
        return

    # 2. DATI
    logger.info("📥 Caricamento dati storici...")
    # Carichiamo abbastanza dati per gli indicatori
    data_map = db.get_ohlc_all_tickers(days=days_history + 100)
    
    if not data_map:
        logger.error("❌ Nessun dato trovato nel DB. Esegui prima il fetch (tester.py o daily_run).")
        return

    # 3. SEGNALI (Vettoriale)
    logger.info("🧠 Calcolo indicatori e segnali...")
    all_signals = strategy.compute(data_map)
    
    if all_signals.empty:
        logger.warning("⚠️ La strategia non ha generato alcun segnale nel periodo.")
        return
    
    # Conversione date per sicurezza
    all_signals['date'] = pd.to_datetime(all_signals['date'])
    all_signals.sort_values('date', inplace=True)

    # 4. SIMULAZIONE (Event Driven)
    logger.info("▶️ Inizio simulazione temporale...")
    
    # Creiamo timeline
    all_dates = sorted(list(set(d for df in data_map.values() for d in df['date'])))
    # Filtriamo date successive all'inizio del backtest effettivo
    start_date = datetime.now() - timedelta(days=days_history)
    sim_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]

    equity_curve = []

    for current_date in sim_dates:
        # A. Aggiornamento Prezzi (Mark-to-Market)
        current_prices = {}
        for ticker, df in data_map.items():
            row = df[df['date'] == current_date]
            if not row.empty:
                current_prices[ticker] = row.iloc[0]['close']
        
        pm.update_market_prices(current_prices)
        
        # B. Risk Management
        # Recuperiamo segnali di OGGI
        daily_signals = all_signals[all_signals['date'] == current_date]
        
        # Injection dati puri
        pos_dict = dict(zip(pm.df_portfolio['ticker'], pm.df_portfolio['size']))
        equity = pm.get_total_equity()
        cash = float(pm.df_cash.iloc[0]['cash']) if not pm.df_cash.empty else 0.0
        
        orders = rm.evaluate(
            signals_df=daily_signals,
            total_equity=equity,
            available_cash=cash,
            current_positions=pos_dict
        )
        
        # C. Esecuzione (Al prezzo di chiusura del segnale)
        for order in orders:
            # Simuliamo esecuzione perfetta
            pm.execute_order(order)
            
            # (Opzionale) Debug log
            # logger.debug(f"Executed {order['action']} {order['ticker']}")

        # D. Logging
        equity_curve.append({
            "date": current_date,
            "equity": pm.get_total_equity(),
            "cash": pm.df_cash.iloc[0]['cash'] if not pm.df_cash.empty else 0.0
        })

    # 5. RISULTATI
    df_result = pd.DataFrame(equity_curve)
    final_equity = df_result.iloc[-1]['equity']
    
    # Analisi dei Trade
    analyze_trades(pm.df_trades, initial_capital, final_equity)
    
    # Export CSV per analisi esterna (es. Excel/Google Sheets)
    output_file = f"data/backtest_{strategy_name}_{datetime.now().strftime('%Y%m%d')}.csv"
    df_result.to_csv(output_file, index=False)
    logger.info(f"💾 Dati equity salvati in: {output_file}")

if __name__ == "__main__":
    run_backtest("RSI", days_history=365*3)