import pytest
from src.portfolio_manager import PortfolioManager

@pytest.fixture
def pm():
    """Fixture per avere un portfolio pulito ad ogni test."""
    manager = PortfolioManager()
    manager.update_cash(10000.0) # Partiamo con 10k
    return manager

def test_portfolio_buy_execution(pm):
    """Testa aggiornamento cassa e posizioni dopo un BUY."""
    order = {
        "ticker": "AAPL",
        "action": "BUY",
        "quantity": 10,
        "price": 150.0,
        "stop_loss": 140.0,
        "take_profit": 170.0
    }
    
    pm.execute_order(order)
    
    # 1. Verifica Cassa
    # 10.000 - (10 * 150) = 8.500
    assert pm.df_cash.iloc[0]['cash'] == 8500.0
    
    # 2. Verifica Posizione
    pos = pm.df_portfolio.iloc[0]
    assert pos['ticker'] == "AAPL"
    assert pos['size'] == 10
    assert pos['price'] == 150.0
    
    # 3. Verifica Equity Totale (Cash + Asset) deve rimanere invariata subito dopo l'acquisto
    assert pm.get_total_equity() == 10000.0

def test_portfolio_sell_execution(pm):
    """Testa la chiusura di una posizione."""
    # Setup: Compriamo prima
    pm.execute_order({"ticker": "AAPL", "action": "BUY", "quantity": 10, "price": 100.0})
    
    # Action: Vendiamo tutto a profitto (110)
    pm.execute_order({"ticker": "AAPL", "action": "SELL", "quantity": 10, "price": 110.0})
    
    # 1. Verifica Cassa
    # 9000 (post buy) + 1100 (sell) = 10100
    assert pm.df_cash.iloc[0]['cash'] == 10100.0
    
    # 2. Verifica Posizione rimossa
    assert pm.df_portfolio.empty

def test_portfolio_mark_to_market(pm):
    """Testa l'aggiornamento dei prezzi di mercato."""
    pm.execute_order({"ticker": "AAPL", "action": "BUY", "quantity": 10, "price": 100.0})
    
    # Il mercato sale a 120
    pm.update_market_prices({"AAPL": 120.0})
    
    # Equity deve salire
    # Cash (9000) + Asset (10 * 120 = 1200) = 10200
    assert pm.get_total_equity() == 10200.0