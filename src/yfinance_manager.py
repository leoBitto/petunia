# src/yfinance_manager.py
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

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
        end_date = datetime.utcnow().date()
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

        df_flat = data.stack(level=0, future_stack=True).reset_index()
        df_flat['Date'] = df_flat['Date'].dt.date
        all_data = list(df_flat[['Ticker','Date','Open','High','Low','Close','Volume']].itertuples(index=False, name=None))

        return all_data


    def fetch_history(self, tickers: List[str], years: int = 3, threads: bool = True, auto_adjust: bool = False) -> List[Dict]:
        """
        Recupera i dati storici fino a `years` anni fa per bootstrap iniziale.
        """
        days = years * 365
        self.logger.info(f"Fetching {years} year(s) of history ({days} days)...")
        return self.fetch_ohlc(tickers, days=days, threads=threads, auto_adjust=auto_adjust)
