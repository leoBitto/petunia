# scripts/tester.py
from src.database_manager import DatabaseManager

def main():
    print("[TEST] Inizializzazione DatabaseManager e creazione schema...")
    try:
        db = DatabaseManager()
        db.init_schema()
        print("[OK] Schema creato correttamente nel database.")
    except Exception as e:
        print(f"[ERRORE] {e}")
    finally:
        if db:
            db.close()
            print("[INFO] Connessione al DB chiusa.")

if __name__ == "__main__":
    main()
