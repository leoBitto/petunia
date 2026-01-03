import pandas as pd
import numpy as np
from typing import Dict
from .base import StrategyBase

class StrategyEMA(StrategyBase):
    """
    Strategia Trend Following basata su incrocio medie mobili esponenziali (EMA).
    Segnale BUY: EMA_short > EMA_long
    Segnale SELL: EMA_short < EMA_long
    """

    def __init__(self, short_window: int = 50, long_window: int = 200, atr_period: int = 14):
        super().__init__("EMA_Crossover")
        self.short_window = short_window
        self.long_window = long_window
        self.atr_period = atr_period

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calcolo ATR manuale (identico a RSI, potremmo portarlo in Base in futuro)."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1.0/period, adjust=False).mean()

    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals_list = []
        self.logger.info(f"Avvio strategia EMA Cross ({self.short_window}/{self.long_window}) su {len(data_map)} ticker.")

        for ticker, df in data_map.items():
            # 1. Validazione Dati
            if len(df) < self.long_window:
                continue

            df = df.copy().sort_values('date')

            # 2. Calcolo Indicatori
            try:
                df['EMA_short'] = df['close'].ewm(span=self.short_window, adjust=False).mean()
                df['EMA_long'] = df['close'].ewm(span=self.long_window, adjust=False).mean()
                df['ATR'] = self._calculate_atr(df, self.atr_period)
            except Exception as e:
                self.logger.error(f"Errore calcolo math {ticker}: {e}")
                continue

            # 3. Analisi Ultima Riga
            last_row = df.iloc[-1]
            ema_s = last_row['EMA_short']
            ema_l = last_row['EMA_long']
            atr_val = last_row['ATR']
            price = last_row['close']

            if pd.isna(ema_s) or pd.isna(ema_l) or pd.isna(atr_val):
                continue

            # 4. Logica Trading
            # Trend Following: Se short > long siamo in trend UP -> BUY/HOLD
            # Se short < long siamo in trend DOWN -> SELL
            
            signal = "HOLD"
            if ema_s > ema_l:
                signal = "BUY"
            elif ema_s < ema_l:
                signal = "SELL"

            # 5. Output
            signals_list.append({
                "ticker": ticker,
                "date": last_row['date'],
                "signal": signal,
                "atr": atr_val,
                "price": price,
                "meta": {
                    "ema_short": round(ema_s, 2),
                    "ema_long": round(ema_l, 2),
                    "diff": round(ema_s - ema_l, 2)
                }
            })

        if not signals_list:
            return pd.DataFrame(columns=['ticker', 'date', 'signal', 'atr', 'meta'])
            
        return pd.DataFrame(signals_list)