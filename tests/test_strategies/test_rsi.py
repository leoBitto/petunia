import pytest
from src.strategies import StrategyRSI
from .test_validate_contract import validate_strategy_output

@pytest.fixture
def strategy():
    # Setup RSI standard (14 periodi)
    return StrategyRSI(rsi_period=14, rsi_lower=30, rsi_upper=70)

def test_rsi_uptrend(strategy, market_uptrend):
    """
    In un uptrend costante (lento), l'RSI sta sopra 50 ma potrebbe non scattare SELL (>70)
    se la salita è graduale. L'importante è che NON sia BUY (<30).
    """
    results = strategy.compute(market_uptrend)
    validate_strategy_output(results)
    
    last_signal = results.iloc[-1]['signal']
    # Sicuramente non devo comprare in un uptrend "già partito" per mean reversion (RSI alto)
    assert last_signal in ["HOLD", "SELL"] 

def test_rsi_downtrend(strategy, market_downtrend):
    """
    In un downtrend costante, l'RSI sta sotto 50. 
    Non deve essere SELL (>70).
    """
    results = strategy.compute(market_downtrend)
    validate_strategy_output(results)
    
    last_signal = results.iloc[-1]['signal']
    # Sicuramente non vendo se è già crollato
    assert last_signal in ["HOLD", "BUY"]

def test_rsi_sideways(strategy, market_sideways):
    """
    Il terreno di caccia dell'RSI. Qui validiamo solo il contratto.
    """
    results = strategy.compute(market_sideways)
    validate_strategy_output(results)
    
    last_signal = results.iloc[-1]['signal']
    assert last_signal in ["BUY", "SELL", "HOLD"]