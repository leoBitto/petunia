import pandas as pd
import numpy as np
from typing import Dict
from src.strategy_base import StrategyBase

class StrategyRSI(StrategyBase):
    """
    Strategia Mean Reversion basata su RSI (Relative Strength Index).
    Implementazione NATIVA (No pandas-ta) per massima stabilità.
    """

    def __init__(self, rsi_period: int = 14, rsi_lower: int = 30, rsi_upper: int = 70, atr_period: int = 14):
        super().__init__("RSI_MeanReversion")
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.atr_period = atr_period

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calcolo RSI manuale usando Wilder's Smoothing (equivalente a pandas-ta)."""
        delta = series.diff()
        
        # Separiamo guadagni e perdite
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # Wilder's Smoothing usa alpha = 1/period
        alpha = 1.0 / period
        
        avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calcolo ATR manuale."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range Calculation
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        # Prende il massimo tra i 3 metodi per ogni riga
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR è la media mobile esponenziale (Wilder's) del TR
        atr = tr.ewm(alpha=1.0/period, adjust=False).mean()
        return atr

    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals_list = []
        
        self.logger.info(f"Avvio strategia RSI (Native) su {len(data_map)} ticker.")

        for ticker, df in data_map.items():
            # 1. Validazione
            min_rows = max(self.rsi_period, self.atr_period) + 5
            if len(df) < min_rows:
                continue

            # Lavoriamo su una copia per non sporcare i dati originali
            df = df.copy().sort_values('date')

            try:
                # 2. Calcolo Indicatori Manuale
                df['RSI'] = self._calculate_rsi(df['close'], self.rsi_period)
                df['ATR'] = self._calculate_atr(df, self.atr_period)
            except Exception as e:
                self.logger.error(f"Errore calcolo math {ticker}: {e}")
                continue

            # 3. Analisi Ultima Riga
            last_row = df.iloc[-1]
            rsi_val = last_row['RSI']
            atr_val = last_row['ATR']
            price = last_row['close']

            if pd.isna(rsi_val) or pd.isna(atr_val):
                continue

            # 4. Logica Trading
            signal = "HOLD"
            if rsi_val < self.rsi_lower:
                signal = "BUY"
            elif rsi_val > self.rsi_upper:
                signal = "SELL"

            # 5. Output
            signals_list.append({
                "ticker": ticker,
                "date": last_row['date'],
                "signal": signal,
                "atr": atr_val,
                "price": price,
                "meta": {
                    "rsi": round(rsi_val, 2),
                    "note": f"RSI: {rsi_val:.2f}"
                }
            })

        if not signals_list:
            return pd.DataFrame(columns=['ticker', 'date', 'signal', 'atr', 'meta'])
            
        return pd.DataFrame(signals_list)