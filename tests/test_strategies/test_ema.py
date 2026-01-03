import pytest
from src.strategies import StrategyEMA
# Importiamo il validatore che si trova nella stessa cartella
from .test_validate_contract import validate_strategy_output

@pytest.fixture
def strategy():
    # Setup strategia standard per i test
    return StrategyEMA(short_window=20, long_window=50)

def test_ema_uptrend(strategy, market_uptrend):
    """Mercato Toro: EMA veloce > lenta -> BUY"""
    results = strategy.compute(market_uptrend)
    
    # 1. Contratto
    validate_strategy_output(results)
    
    # 2. Logica
    last_signal = results.iloc[-1]['signal']
    assert last_signal == "BUY", "Errore Logica: In uptrend costante mi aspetto BUY"

def test_ema_downtrend(strategy, market_downtrend):
    """Mercato Orso: EMA veloce < lenta -> SELL"""
    results = strategy.compute(market_downtrend)
    
    validate_strategy_output(results)
    
    last_signal = results.iloc[-1]['signal']
    assert last_signal == "SELL", "Errore Logica: In downtrend costante mi aspetto SELL"

def test_ema_sideways(strategy, market_sideways):
    """Mercato Laterale: Contratto valido, segnale esistente"""
    results = strategy.compute(market_sideways)
    
    validate_strategy_output(results)
    
    last_signal = results.iloc[-1]['signal']
    assert last_signal in ["BUY", "SELL", "HOLD"]