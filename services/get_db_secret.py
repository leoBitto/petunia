# services/get_db_secret.py
import json
import sys
import logging

# Disabilitiamo i log per avere solo output JSON
logging.disable(logging.CRITICAL)
from src.drive_manager import DriveManager

def get_db_credentials() -> dict:
    """
    Restituisce un dizionario contenente le credenziali del DB
    prese dal Secret Manager.
    """
    try:
        dm = DriveManager()
        secret = dm._get_secret("db_info")
        return secret
    except Exception as e:
        raise RuntimeError(f"Errore nel recupero dei secrets DB: {e}")

def main():
    try:
        creds = get_db_credentials()
        print(json.dumps(creds))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
