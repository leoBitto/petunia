# services/init_db.py
import sys
from src.database_manager import DatabaseManager
from src.logger import get_logger

def main():
    logger = get_logger("InitDB")
    logger.info("🛠️ Inizializzazione Schema Database...")
    
    try:
        db = DatabaseManager()
        db.init_schema() # Chiama la funzione che crea le tabelle
        logger.info("✅ Tabelle create (o già esistenti) con successo.")
    except Exception as e:
        logger.error(f"❌ Errore critico durante init_db: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()