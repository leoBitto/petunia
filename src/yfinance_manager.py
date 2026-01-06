# src/yfinance_manager.py
from typing import List, Dict, Tuple
from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf
import numpy as np

from src.logger import get_logger


class YFinanceManager:
    """
    Gestisce il recupero e la pulizia di dati OHLCV da Yahoo Finance.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def fetch_ohlc(self, tickers: List[str], days: int = 30, threads: bool = True, auto_adjust: bool = False) -> List[Dict]:
        """
        Recupera dati OHLCV per i ticker indicati dagli ultimi `days` giorni.
        - threads: abilita il threading nativo di yfinance
        - auto_adjust: passato esplicitamente a yf.download per rimuovere il FutureWarning
        Restituisce lista di dict: [{ticker, date, open, high, low, close, volume}, ...]
        """
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        self.logger.info(f"Fetching OHLCV for {len(tickers)} ticker(s) from {start_date} to {end_date}")

        try:
            data = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                progress=False,
                group_by="ticker",
                threads=threads,
                auto_adjust=auto_adjust,  # *** esplicito per sopprimere FutureWarning ***
            )
        except Exception as e:
            self.logger.error(f"Errore durante il fetch da yfinance: {e}")
            return []


        cleaned = self._normalize_data(data, tickers)
        self.logger.info(f"Fetched {len(cleaned)} OHLCV records from Yahoo Finance.")

        return cleaned

    def _normalize_data(self, data: pd.DataFrame, tickers: List) -> List[Tuple]:
        all_data: List[Tuple] = []

        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            self.logger.warning("Nessun dato ricevuto da yfinance (data è vuoto).")
            return all_data

        # Gestione Multi-Index vs Single-Index
        # Se scarichiamo 1 solo ticker, yfinance non usa il MultiIndex sulle colonne.
        if isinstance(data.columns, pd.MultiIndex):
            df_flat = data.stack(level=0, future_stack=True).reset_index()
        else:
            # Caso singolo ticker: aggiungiamo la colonna Ticker manualmente
            df_flat = data.reset_index()
            df_flat['Ticker'] = tickers[0] if tickers else "UNKNOWN"

        # Rinominiamo la colonna Date/Datetime se necessario
        if 'Date' in df_flat.columns:
            df_flat['date_col'] = df_flat['Date']
        elif 'Datetime' in df_flat.columns:
            df_flat['date_col'] = df_flat['Datetime']
        else:
            self.logger.error("Colonna data non trovata nel DataFrame.")
            return []

        # Conversione e Pulizia Data
        df_flat['date_col'] = pd.to_datetime(df_flat['date_col']).dt.date
        
        # --- SANITIZZAZIONE VOLUME (FIX BIGINT ERROR) ---
        # 1. Sostituisce NaN con 0
        df_flat['Volume'] = df_flat['Volume'].fillna(0)
        
        # 2. Rimuove infiniti (+inf, -inf)
        df_flat = df_flat.replace([np.inf, -np.inf], 0)

        # 3. Clamping (Taglio valori eccessivi)
        # Il max di Postgres BIGINT è ~9.22 * 10^18. 
        # Impostiamo un limite sicuro (es. 10^15) che è comunque irraggiungibile per volumi reali.
        MAX_BIGINT_SAFE = 10**15 
        df_flat['Volume'] = df_flat['Volume'].clip(upper=MAX_BIGINT_SAFE)

        # 4. Conversione finale a Intero
        df_flat['Volume'] = df_flat['Volume'].astype(int)
        # ------------------------------------------------

        # Selezione colonne finali
        # Assicuriamoci che l'ordine sia quello atteso dal DatabaseManager
        # (ticker, date, open, high, low, close, volume)
        try:
            target_df = df_flat[['Ticker', 'date_col', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except KeyError as e:
            self.logger.error(f"Colonne mancanti nel DataFrame normalizzato: {e}")
            return []

        # Conversione in lista di tuple (più veloce per psycopg)
        all_data = list(target_df.itertuples(index=False, name=None))

        return all_data


    def fetch_history(self, tickers: List[str], years: int = 3, threads: bool = True, auto_adjust: bool = False) -> List[Dict]:
        """
        Recupera i dati storici fino a `years` anni fa per bootstrap iniziale.
        """
        days = years * 365
        self.logger.info(f"Fetching {years} year(s) of history ({days} days)...")
        return self.fetch_ohlc(tickers, days=days, threads=threads, auto_adjust=auto_adjust)
