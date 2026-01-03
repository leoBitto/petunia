import pytest
import pandas as pd
from src.risk_manager import RiskManager

def test_risk_buy_logic(mock_uptrend):
    """Verifica calcolo Size e Stop Loss per un ordine BUY."""
    rm = RiskManager(risk_per_trade=0.02, stop_atr_multiplier=2.0)
    
    # Creiamo un segnale sintetico
    signal_row = pd.Series({
        "ticker": "TEST_TKR",
        "signal": "BUY",
        "price": 100.0,
        "atr": 5.0,
        "meta": {}
    })
    signals_df = pd.DataFrame([signal_row])
    
    # Scenario: 10k Equity, 10k Cash, Nessuna posizione
    orders = rm.evaluate(
        signals_df, 
        total_equity=10000, 
        available_cash=10000, 
        current_positions={}
    )
    
    assert len(orders) == 1
    order = orders[0]
    
    # VALIDAZIONE MATEMATICA
    # Rischio = 10.000 * 0.02 = 200€
    # Stop Distance = 5.0 * 2.0 = 10€
    # Shares = 200 / 10 = 20
    assert order['action'] == "BUY"
    assert order['quantity'] == 20
    assert order['stop_loss'] == 90.0  # 100 - 10
    assert order['take_profit'] == 120.0 # 100 + (10 * 2) Default 2R

def test_risk_contract_compliance(mock_uptrend):
    """Verifica che l'ordine rispetti il CONTRATTO (Schema Validation)."""
    rm = RiskManager()
    
    # Segnale Finto
    signals_df = pd.DataFrame([{
        "ticker": "TEST", "signal": "BUY", "price": 50, "atr": 1, "meta": {}
    }])
    
    orders = rm.evaluate(signals_df, 10000, 10000, {})
    
    # SCHEMA OBBLIGATORIO
    REQUIRED_KEYS = {'ticker', 'action', 'quantity', 'price', 'stop_loss', 'meta'}
    
    for order in orders:
        # 1. Verifica Chiavi
        missing = REQUIRED_KEYS - set(order.keys())
        assert not missing, f"Ordine incompleto. Mancano: {missing}"
        
        # 2. Verifica Tipi
        assert isinstance(order['quantity'], int), "Quantity deve essere intero"
        assert isinstance(order['price'], (float, int)), "Price deve essere numerico"
        assert isinstance(order['stop_loss'], (float, int)), "Stop Loss deve essere numerico"

def test_risk_sell_logic():
    """Verifica che generi ordini di vendita se richiesto."""
    rm = RiskManager()
    
    # Segnale SELL
    signals_df = pd.DataFrame([{
        "ticker": "OLD_POS", "signal": "SELL", "price": 100, "atr": 2, "meta": {}
    }])
    
    # Abbiamo 50 azioni in portafoglio
    current_positions = {"OLD_POS": 50}
    
    orders = rm.evaluate(signals_df, 10000, 10000, current_positions)
    
    assert len(orders) == 1
    assert orders[0]['action'] == "SELL"
    assert orders[0]['quantity'] == 50 # Vende tutto