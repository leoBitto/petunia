import pandas as pd
import numpy as np
from typing import Dict
from .base import StrategyBase

class StrategyEMA(StrategyBase):
    def __init__(self, short_window: int = 50, long_window: int = 200, atr_period: int = 14):
        super().__init__("EMA_Crossover")
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self.atr_period = int(atr_period)

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()

    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals_list = []
        self.logger.info(f"Avvio strategia EMA (Vectorized) su {len(data_map)} ticker.")

        for ticker, df in data_map.items():
            if len(df) < self.long_window:
                continue

            d = df.copy().sort_values('date')

            # 1. Calcolo Indicatori
            d['ema_short'] = d['close'].ewm(span=self.short_window, adjust=False).mean()
            d['ema_long'] = d['close'].ewm(span=self.long_window, adjust=False).mean()
            d['atr'] = self._calculate_atr(d, self.atr_period)

            # 2. Logica Vettoriale
            d['signal'] = 'HOLD'
            # BUY: Quando la Short è SOPRA la Long (Trend Up)
            d.loc[d['ema_short'] > d['ema_long'], 'signal'] = 'BUY'
            # SELL: Quando la Short è SOTTO la Long (Trend Down)
            d.loc[d['ema_short'] < d['ema_long'], 'signal'] = 'SELL'

            # 3. Pulizia
            d.dropna(subset=['ema_short', 'ema_long', 'atr'], inplace=True)

            # 4. Output
            output = d[['date', 'ticker', 'close', 'signal', 'atr']].copy()
            output.rename(columns={'close': 'price'}, inplace=True)
            
            # Meta dati per capire quanto sono distanti le medie
            output['meta'] = output.apply(lambda x: {
                'ema_s': round(x['ema_short'], 2), 
                'ema_l': round(x['ema_long'], 2)
            }, axis=1)

            signals_list.append(output)

        if not signals_list:
            return pd.DataFrame()
            
        return pd.concat(signals_list, ignore_index=True)