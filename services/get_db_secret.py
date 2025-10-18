# services/get_db_secret.py
import json
import sys
import logging

# Disabilitiamo qualsiasi log affinché lo stdout contenga SOLO il JSON
logging.disable(logging.CRITICAL)

# Import dopo aver disabilitato i log
from src.drive_manager import DriveManager

def main():
    try:
        dm = DriveManager()
        secret = dm._get_secret("db_info")
        # stampa SOLO il JSON pulito su stdout
        print(json.dumps(secret))
    except Exception as e:
        # Errori su stdout in JSON con campo "error" e uscita non-zero
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
