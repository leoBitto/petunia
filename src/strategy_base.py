# src/strategy_base.py
from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd
from src.logger import get_logger

class StrategyBase(ABC):
    """
    Classe astratta per tutte le strategie.
    Impone la struttura di input (Dict di DF) e output (DataFrame segnali).
    """
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"Strategy_{name}")

    @abstractmethod
    def compute(self, data_map: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Logica principale della strategia.
        
        Input:
            data_map: Dizionario { 'TICKER': pd.DataFrame(OHLCV) }
                      Il DataFrame contiene storico sufficiente per gli indicatori.
        
        Output:
            pd.DataFrame con colonne: 
            ['ticker', 'date', 'signal', 'atr', 'meta']
            - signal: 'BUY', 'SELL', 'HOLD'
            - atr: Volatilità (utile per il Risk Manager per calcolare lo stop)
            - meta: (Opzionale) score, note, etc.
        """
        pass

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """Utility per check veloci sui dati (es. non vuoto)."""
        if df.empty or len(df) < 5: # Minimo sindacale per calcoli
            return False
        return True