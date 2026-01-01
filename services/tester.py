# scripts/test_yfinance.py
from datetime import datetime, timedelta
from src.yfinance_manager import YFinanceManager
from src.database_manager import DatabaseManager
from src.drive_manager import DriveManager

def main():
    # 1️⃣ Recupero ticker dal Drive
    drive = DriveManager()
    tickers = drive.get_universe_tickers()
    print(f"Paniere recuperato: {tickers}")

    # 2️⃣ Fetch dati OHLCV
    yf_manager = YFinanceManager()
    data = yf_manager.fetch_history(tickers, years=3, threads=True)
    print(f"Totale record ottenuti da YFinance: {len(data)}")

    # 3️⃣ Inserimento batch nel DB
    db = DatabaseManager()
    try:
        db.upsert_ohlc(data)
        print(f"[DB] Inseriti/aggiornati {len(data)} record OHLCV.")

        # 4️⃣ Query di verifica: ultimi 5 giorni per tutti i tickers
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        ohlc_records = db.get_ohlc(tickers, start_date.isoformat(), end_date.isoformat())
        print("[DB] Ultimi record inseriti:")
        for row in ohlc_records:
            print(row)

    except Exception as e:
        print(f"[ERRORE DB] {e}")
    finally:
        db.close()
        print("[INFO] Connessione al DB chiusa.")

if __name__ == "__main__":
    main()
