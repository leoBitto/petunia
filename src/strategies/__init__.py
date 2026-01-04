from .base import StrategyBase
from .rsi import StrategyRSI
from .ema import StrategyEMA

# Mappa dei nomi strategia alle classi
STRATEGY_MAP = {
    "RSI": StrategyRSI,
    "EMA": StrategyEMA
    # Qui aggiungerai le future strategie (es. "BOLLINGER": StrategyBollinger)
}

def get_strategy(strategy_name: str, **kwargs) -> StrategyBase:
    """
    Factory Method: Istanzia e restituisce la strategia richiesta.
    
    Args:
        strategy_name (str): Nome della strategia (es. "RSI", "EMA").
        **kwargs: Parametri specifici (es. rsi_period=14, short_window=50).
        
    Returns:
        StrategyBase: L'istanza della strategia configurata.
        
    Raises:
        ValueError: Se il nome della strategia non è supportato.
    """
    if strategy_name not in STRATEGY_MAP:
        raise ValueError(f"Strategia '{strategy_name}' non trovata. Disponibili: {list(STRATEGY_MAP.keys())}")
    
    strategy_class = STRATEGY_MAP[strategy_name]
    
    # Istanziamo la classe passando i parametri spacchettati
    return strategy_class(**kwargs)