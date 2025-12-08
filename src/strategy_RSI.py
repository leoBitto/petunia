import pandas as pd
import pandas_ta as ta
from typing import Dict
from src.strategy_base import StrategyBase

class StrategyRSI(StrategyBase):
    """
    Strategia Mean Reversion basata su RSI (Relative Strength Index).
    
    Riferimenti dal Wiki:
    - Buy Zone: RSI < 30 (Oversold)
    - Sell Zone: RSI > 70 (Overbought)
    - Risk Mgmt: Calcola ATR per impostare Stop Loss a 2x ATR
    """

    def __init__(self, rsi_period: int = 14, rsi_lower: int = 30, rsi_upper: int = 70, atr_period: int = 14):
        super().__init__("RSI_MeanReversion")
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.atr_period = atr_period

    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        signals_list = []
        
        self.logger.info(f"Avvio strategia RSI (Period: {self.rsi_period}) su {len(data_map)} ticker.")

        for ticker, df in data_map.items():
            # 1. Validazione Dati
            # Serve abbastanza storico per RSI e ATR
            min_rows = max(self.rsi_period, self.atr_period) + 5
            if len(df) < min_rows:
                continue

            # Lavoriamo su una copia
            df = df.copy()

            # 2. Calcolo Indicatori (Pandas-TA)
            try:
                # Calcolo RSI
                df.ta.rsi(length=self.rsi_period, append=True)
                # Calcolo ATR (Fondamentale per il Risk Manager)
                df.ta.atr(length=self.atr_period, append=True)
            except Exception as e:
                self.logger.error(f"Errore indicatori {ticker}: {e}")
                continue

            # 3. Recupero Valori
            # Nomi colonne dinamici generati da pandas-ta (es. "RSI_14", "ATRr_14")
            col_rsi = f"RSI_{self.rsi_period}"
            # ATR può avere nomi diversi a seconda della versione, lo cerchiamo
            col_atr = f"ATRr_{self.atr_period}" 
            if col_atr not in df.columns:
                 # Fallback: a volte pandas-ta lo chiama diversamente o è l'ultima colonna aggiunta
                 col_atr = [c for c in df.columns if "ATR" in c][-1]

            last_row = df.iloc[-1]
            
            rsi_val = last_row.get(col_rsi)
            atr_val = last_row.get(col_atr, 0.0)

            if pd.isna(rsi_val):
                continue

            # 4. Logica di Trading (KISS: Keep It Simple)
            # Il wiki dice: "starts to reverse when it points down from 70... and up from 30"
            # Implementazione Base: Compra se siamo in zona ipervenduto, Vendi se ipercomprato.
            
            signal = "HOLD"

            if rsi_val < self.rsi_lower:
                signal = "BUY"
                # Nota: Una strategia più avanzata controllerebbe se rsi_val > rsi_ieri 
                # per confermare l'inversione come suggerito dal testo, ma per ora teniamo semplice.
            
            elif rsi_val > self.rsi_upper:
                signal = "SELL"

            # 5. Output
            signals_list.append({
                "ticker": ticker,
                "date": last_row['date'],
                "signal": signal,
                "atr": atr_val,  # Il Risk Manager userà questo per: Stop Loss = Price - (2 * ATR)
                "price": last_row['close'],
                "meta": {
                    "rsi": rsi_val,
                    "note": f"RSI: {rsi_val:.2f} (Triggers: <{self.rsi_lower}, >{self.rsi_upper})"
                }
            })

        if not signals_list:
            return pd.DataFrame(columns=['ticker', 'date', 'signal', 'atr', 'meta'])
            
        return pd.DataFrame(signals_list)