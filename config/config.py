import os
from pathlib import Path
from dotenv import load_dotenv

# Carica il .env locale se presente (utile per sviluppo fuori da docker)
load_dotenv()

class Config:
    # 1. DATABASE
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "db") # Default 'db' per rete docker
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "money_db")

    # 2. GOOGLE CLOUD
    # Il percorso è fisso perché Docker lo monterà sempre qui
    GOOGLE_KEY_PATH = Path("/app/config/credentials/service_account.json")
    
    # IDs Sheets
    UNIVERSE_SHEET_ID = os.getenv("UNIVERSE_SHEET_ID")
    REPORT_SHEET_ID = os.getenv("REPORT_SHEET_ID")
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    
    # 3. APP
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()