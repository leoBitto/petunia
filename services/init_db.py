import sys
from src.database_manager import DatabaseManager
from src.drive_manager import DriveManager
from src.yfinance_manager import YFinanceManager
from src.logger import get_logger

def main():
    logger = get_logger("InitDB")
    logger.info("🛠️  AVVIO INIZIALIZZAZIONE SISTEMA...")
    
    try:
        # 1. INIT DB SCHEMA
        logger.info("--- FASE 1: Schema Database ---")
        db = DatabaseManager()
        db.init_schema()
        logger.info("✅ Tabelle verificate/create.")

        # 2. CARICAMENTO UNIVERSE (DA GOOGLE SHEETS)
        logger.info("--- FASE 2: Caricamento Universe ---")
        drive = DriveManager()
        tickers = drive.get_universe_tickers()
        
        if not tickers:
            logger.warning("⚠️  Nessun ticker trovato nel Google Sheet. Impossibile scaricare storico.")
            # Non crashiamo, magari l'utente vuole solo le tabelle vuote
            return

        logger.info(f"✅ Trovati {len(tickers)} ticker: {tickers}")

        # 3. DOWNLOAD STORICO (BOOTSTRAP DATI)
        logger.info("--- FASE 3: Download Storico (1 Anno) ---")
        yf_man = YFinanceManager()
        
        # Scarichiamo 1 anno (365 giorni)
        historical_data = yf_man.fetch_history(tickers, years=1)
        
        if not historical_data:
            logger.warning("⚠️  Nessun dato storico ricevuto da Yahoo Finance.")
            return

        # 4. SALVATAGGIO NEL DB
        logger.info(f"💾 Salvataggio di {len(historical_data)} righe nel database...")
        db.upsert_ohlc(historical_data)
        logger.info("✅ Storico salvato correttamente.")

        logger.info("🚀 INIZIALIZZAZIONE COMPLETATA CON SUCCESSO.")

    except Exception as e:
        logger.error(f"❌ Errore critico durante init_db: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()