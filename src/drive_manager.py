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
    Si occupa di:
    1. Autenticazione sicura via Google Secret Manager.
    2. Lettura Ticker (Universe).
    3. Gestione Ordini Pendenti (Lettura/Scrittura su Sheet condiviso).
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
            return secret_data
        except Exception as e:
            self.logger.error(f"Errore recupero secret '{secret_name}': {e}")
            raise

    def _authenticate(self):
        """Autentica il client gspread usando il Service Account recuperato dal Secret Manager."""
        try:
            service_account_info = self._get_secret(config.SERVICE_ACCOUNT_SECRET_NAME)
            creds = Credentials.from_service_account_info(
                service_account_info, scopes=self.DEFAULT_SCOPES
            )
            self.gsheet_client = gspread.authorize(creds)
            self.logger.info("Autenticazione Google Sheets completata.")
        except Exception as e:
            self.logger.critical(f"Errore autenticazione Google: {e}")
            raise

    def _get_worksheet(self, sheet_id: str, tab_name: str):
        """Helper sicuro per ottenere un worksheet."""
        try:
            # Apre lo spreadsheet per ID
            spreadsheet = self.gsheet_client.open_by_key(sheet_id)
            # Cerca il tab specifico
            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                self.logger.warning(f"Tab '{tab_name}' non trovato. Creazione in corso...")
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows=100, cols=10)
            return worksheet
        except Exception as e:
            self.logger.error(f"Errore accesso Sheet {sheet_id} / Tab {tab_name}: {e}")
            raise

    # --- METODI PUBBLICI ---

    def get_universe_tickers(self) -> list[str]:
        """Legge la lista dei ticker dal foglio Universe."""
        try:
            # Assumiamo che UNIVERSE_SHEET_ID contenga un tab (es. 'Sheet1' o 'Universe')
            sheet = self.gsheet_client.open_by_key(config.UNIVERSE_SHEET_ID).sheet1
            data = sheet.get_all_values()
            
            if not data:
                return []

            df = pd.DataFrame(data[1:], columns=data[0])
            # Pulizia robusta
            tickers = df["Ticker"].dropna().astype(str).str.strip().str.upper().tolist()
            # Rimuove stringhe vuote
            tickers = [t for t in tickers if t]
            
            self.logger.info(f"Universe caricato: {len(tickers)} ticker.")
            return tickers
        except Exception as e:
            self.logger.error(f"Errore lettura Universe: {e}")
            return []

    def get_pending_orders(self) -> list:
        """Legge gli ordini pendenti dal tab 'Orders' del Report Sheet."""
        try:
            sheet = self._get_worksheet(config.REPORT_SHEET_ID, "Orders")
            orders = sheet.get_all_records() # Restituisce lista di dict
            
            clean_orders = []
            for o in orders:
                if not o.get("ticker"): continue # Salta righe vuote
                
                # Conversione tipi (GSheet ritorna stringhe o numeri misti)
                try:
                    # Gestione robusta per numeri che potrebbero arrivare come "10" o 10 o "150,5"
                    qty = o.get("quantity", 0)
                    price = str(o.get("price", "0")).replace(",", ".")
                    
                    o["quantity"] = int(qty) if qty else 0
                    o["price"] = float(price)
                    clean_orders.append(o)
                except ValueError:
                    self.logger.warning(f"Dati non validi nella riga ordine: {o}")
                    continue
            
            return clean_orders
        except Exception as e:
            self.logger.error(f"Errore lettura Pending Orders: {e}")
            return []

    def save_pending_orders(self, orders: list):
        """Sovrascrive il tab 'Orders' con la nuova lista."""
        try:
            sheet = self._get_worksheet(config.REPORT_SHEET_ID, "Orders")
            sheet.clear()

            # Headers standard
            headers = ["action", "ticker", "quantity", "price", "stop_loss", "take_profit", "reason", "meta"]
            
            if not orders:
                sheet.append_row(headers)
                self.logger.info("Lista ordini vuota salvata su GSheet.")
                return

            # Preparazione dati
            values = []
            for o in orders:
                row = []
                for h in headers:
                    val = o.get(h, "")
                    # Convertiamo meta dict in stringa per non rompere GSheet
                    if h == "meta" and isinstance(val, dict):
                        val = str(val)
                    row.append(val)
                values.append(row)

            # Scrittura batch
            sheet.append_row(headers)
            sheet.append_rows(values)
            self.logger.info(f"Salvati {len(orders)} ordini su GSheet.")

        except Exception as e:
            self.logger.error(f"Errore salvataggio Pending Orders: {e}")