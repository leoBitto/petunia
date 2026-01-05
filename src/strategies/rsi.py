import pandas as pd
import numpy as np
from typing import Dict
from .base import StrategyBase

class StrategyRSI(StrategyBase):
    def __init__(self, rsi_period: int = 14, rsi_lower: int = 30, rsi_upper: int = 70, atr_period: int = 14):
        # Chiamata al costruttore base
        super().__init__("RSI_MeanReversion")
        # Parametri salvati
        self.rsi_period = int(rsi_period)
        self.rsi_lower = int(rsi_lower)
        self.rsi_upper = int(rsi_upper)
        self.atr_period = int(atr_period)

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calcolo RSI manuale."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calcolo ATR manuale."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        return atr

    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals_list = []
        # Log dei parametri ricevuti (per debuggare la tua ipotesi sui parametri)
        self.logger.info(f"RSI Params: Period={self.rsi_period}, Lower={self.rsi_lower}, Upper={self.rsi_upper}")

        for ticker, df in data_map.items():
            if len(df) < self.rsi_period + 5:
                continue
            
            # Copia e ordina
            d = df.copy().sort_values('date')

            # 1. Calcolo Indicatori (TUTTO MINUSCOLO per coerenza)
            d['rsi'] = self._calculate_rsi(d['close'], self.rsi_period)
            d['atr'] = self._calculate_atr(d, self.atr_period)

            # 2. Logica Vettoriale
            d['signal'] = 'HOLD'
            d.loc[d['rsi'] < self.rsi_lower, 'signal'] = 'BUY'
            d.loc[d['rsi'] > self.rsi_upper, 'signal'] = 'SELL'

            # 3. Pulizia
            d.dropna(subset=['rsi', 'atr'], inplace=True)

            # 4. Formattazione Output
            try:
                output = d[['date', 'ticker', 'close', 'signal', 'atr', 'rsi']].copy()
                output.rename(columns={'close': 'price'}, inplace=True)
                
                output['meta'] = output.apply(lambda x: {'rsi': round(x['rsi'], 2)}, axis=1)

                signals_list.append(output)
            except KeyError as e:
                self.logger.error(f"CRASH su {ticker}! Colonne disponibili: {d.columns.tolist()}")
                self.logger.error(f"Errore specifico: {e}")
                raise e

        if not signals_list:
            return pd.DataFrame()

        return pd.concat(signals_list, ignore_index=True)