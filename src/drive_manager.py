# src/drive_manager.py
import json
import pandas as pd
import gspread
from google.cloud import secretmanager
from google.oauth2.service_account import Credentials

from src.logger import get_logger
from config import config


class DriveManager:
    """
    Gestisce l'accesso a Google Drive e Google Sheets.
    Si occupa di autenticarsi tramite Google Secret Manager
    e di fornire metodi per leggere/scrivere dati da Sheets.
    """

    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.gsheet_client = None
        self._authenticate()

    def _get_secret(self, secret_name: str, version: str = "latest") -> dict:
        """Recupera un secret dal Google Cloud Secret Manager."""
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{config.GCP_PROJECT_ID}/secrets/{secret_name}/versions/{version}"
            response = client.access_secret_version(name=secret_path)
            secret_data = json.loads(response.payload.data.decode("UTF-8"))
            self.logger.info(f"Secret '{secret_name}' caricato correttamente.")
            return secret_data
        except Exception as e:
            self.logger.error(f"Errore durante il recupero del secret '{secret_name}': {e}")
            raise

    def _authenticate(self):
        """Autentica il client gspread utilizzando le credenziali del service account."""
        try:
            service_account_info = self._get_secret(config.SERVICE_ACCOUNT_SECRET_NAME)
            creds = Credentials.from_service_account_info(
                service_account_info, scopes=self.DEFAULT_SCOPES
            )
            self.gsheet_client = gspread.authorize(creds)
            self.logger.info("Autenticazione Google Sheets completata.")
        except Exception as e:
            self.logger.error(f"Errore durante l'autenticazione: {e}")
            raise

    def get_universe_tickers(self) -> list[str]:
        """Legge la lista dei ticker dal foglio Universe su Google Sheets."""
        try:
            sheet = self.gsheet_client.open_by_key(config.UNIVERSE_SHEET_ID).sheet1
            data = sheet.get_all_values()
            df = pd.DataFrame(data[1:], columns=data[0])
            tickers = df["Ticker"].dropna().str.strip().str.upper().tolist()
            self.logger.info(f"Lettura Universe completata: {len(tickers)} tickers trovati.")
            return tickers
        except Exception as e:
            self.logger.error(f"Errore durante la lettura del foglio Universe: {e}")
            raise
