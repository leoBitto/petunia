import pandas as pd
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager
from src.yfinance_manager import YFinanceManager
from src.drive_manager import DriveManager
from src.logger import get_logger

logger = get_logger("DailyRun")

# --- FUNZIONE 1: Aggiornamento Dati Mercato ---
def update_market_data(db: DatabaseManager, yf: YFinanceManager, dm: DriveManager, pm: PortfolioManager) -> dict:
    logger.info("📡 Step 1: Aggiornamento Dati Mercato")
    
    # 1. Raccolta Ticker
    universe_tkr = dm.get_universe_tickers()
    portfolio_tkr = pm.df_portfolio["ticker"].tolist()
    
    # Recuperiamo i pendenti dal CLOUD
    pending_orders = dm.get_pending_orders()
    pending_tkr = [o["ticker"] for o in pending_orders]
    
    all_tickers = list(set(universe_tkr + portfolio_tkr + pending_tkr))
    
    # 2. Fetch & Store
    logger.info(f"Scarico OHLCV per {len(all_tickers)} ticker...")
    new_data = yf.fetch_ohlc(all_tickers, days=5) 
    
    if not new_data:
        logger.warning("Nessun dato scaricato.")
        return {}

    db.upsert_ohlc(new_data)
    
    # 3. Snapshot Odierno
    today_market = {}
    for row in new_data:
        t_ticker, t_date, t_open, t_high, t_low, t_close, t_volume = row
        today_market[t_ticker] = {
            "date": t_date,
            "open": float(t_open),
            "high": float(t_high),
            "low": float(t_low),
            "close": float(t_close),
            "volume": int(t_volume)
        }
    return today_market

# --- FUNZIONE 2: Shadow Logic ---
def process_shadow_execution(pm: PortfolioManager, today_market: dict, dm: DriveManager):
    logger.info("🕵️ Step 2: Shadow Execution Logic")
    
    # A. Mark-to-Market
    current_prices = {t: d["close"] for t, d in today_market.items()}
    pm.update_market_prices(current_prices)

    # B. Uscite (SL/TP)
    for _, pos in pm.df_portfolio.copy().iterrows():
        ticker = pos["ticker"]
        if ticker not in today_market: continue
        
        mkt = today_market[ticker]
        sl = pos["stop_loss"]
        tp = pos["profit_take"]
        size = pos["size"]
        
        executed_exit = False
        exit_price = 0.0
        reason = ""

        if pd.notna(sl) and mkt["low"] <= sl:
            exit_price = min(mkt["open"], sl) 
            executed_exit = True
            reason = "STOP LOSS"
        elif pd.notna(tp) and mkt["high"] >= tp:
            exit_price = max(mkt["open"], tp)
            executed_exit = True
            reason = "TAKE PROFIT"
            
        if executed_exit:
            logger.info(f"💥 {reason} TRIGGERED su {ticker}. Vendo {size} @ {exit_price:.2f}")
            pm.execute_order({
                "ticker": ticker, "action": "SELL", 
                "quantity": size, "price": exit_price, "reason": reason
            })

    # C. Entrate (Ordini Pendenti da Drive)
    pending_orders = dm.get_pending_orders()
    if not pending_orders: return

    remaining_orders = []
    executed_count = 0
    
    for order in pending_orders:
        ticker = order["ticker"]
        limit_price = float(order["price"])
        
        if ticker not in today_market:
            remaining_orders.append(order)
            continue
            
        mkt = today_market[ticker]
        
        # Logica BUY LIMIT
        if order["action"] == "BUY" and mkt["low"] <= limit_price:
            exec_price = min(mkt["open"], limit_price)
            logger.info(f"⚡ ORDER FILLED {ticker}: Limit {limit_price} -> Exec @ {exec_price:.2f}")
            
            order["price"] = exec_price
            pm.execute_order(order)
            executed_count += 1
        else:
            remaining_orders.append(order)
    
    # D. Aggiornamento Cloud
    # Se abbiamo eseguito qualcosa, carichiamo su Drive solo quelli RIMASTI
    if executed_count > 0:
        dm.save_pending_orders(remaining_orders)
        logger.info(f"Ordini Drive aggiornati: {executed_count} eseguiti, {len(remaining_orders)} rimanenti.")

def main():
    logger.info("🌅 Inizio Daily Run System...")
    try:
        db = DatabaseManager()
        pm = PortfolioManager()
        yf = YFinanceManager()
        dm = DriveManager()
    except Exception as e:
        logger.critical(f"Errore init managers: {e}")
        return

    pm.load_from_db(db.load_portfolio())
    logger.info(f"Equity Iniziale: {pm.get_total_equity():.2f}")

    today_market = update_market_data(db, yf, dm, pm)
    
    if today_market:
        process_shadow_execution(pm, today_market, dm)
        db.save_portfolio(pm.get_snapshot())
        logger.info(f"✅ Daily Run terminata. Equity Finale: {pm.get_total_equity():.2f}")
    else:
        logger.error("❌ Daily Run interrotta: No Data.")

if __name__ == "__main__":
    main()