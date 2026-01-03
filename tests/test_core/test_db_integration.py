import pytest
from datetime import date
import pandas as pd

def test_db_ohlc_lifecycle(test_db):
    """
    Scrive OHLC, legge OHLC e verifica.
    Usa il DB reale (che viene pulito dalla fixture).
    """
    # Calcoliamo date dinamiche
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    
    # 1. Prepare Data (Usiamo le date calcolate)
    raw_data = [
        ("TEST_A", two_days_ago, 100, 110, 90, 105, 1000),
        ("TEST_A", yesterday,    105, 115, 95, 110, 2000),
        ("TEST_B", two_days_ago, 50,  55,  45, 52,  500)
    ]
    
    # 2. Insert (Upsert)
    test_db.upsert_ohlc(raw_data)
    
    fetched = test_db.get_ohlc(["TEST_A"], "2024-01-01", "2024-01-05")
    
    ## 3. Retrieve (Range specifico)
    # Convertiamo le date in stringa ISO per sicurezza nella query
    fetched = test_db.get_ohlc(["TEST_A"], two_days_ago.isoformat(), today.isoformat())
    
    assert len(fetched) == 2
    assert fetched[0]['ticker'] == "TEST_A"
    assert float(fetched[0]['close']) == 105.0 
    
    # 4. Retrieve ALL (Il punto che falliva)
    # Ora funzionerà perché i dati sono di "ieri", quindi sicuramente negli ultimi 365 giorni
    all_data_map = test_db.get_ohlc_all_tickers(days=365)
    
    assert "TEST_A" in all_data_map
    assert "TEST_B" in all_data_map
    assert len(all_data_map["TEST_A"]) == 2

def test_db_portfolio_persistence(test_db):
    """
    Salva lo stato del portafoglio e lo ricarica.
    """
    # 1. Create Fake State
    df_port = pd.DataFrame([{
        "ticker": "NVDA", "size": 5, "price": 400.0, 
        "stop_loss": 380.0, "profit_take": 450.0, 
        "updated_at": pd.Timestamp.now()
    }])
    
    df_cash = pd.DataFrame([{
        "cash": 12345.67, "currency": "EUR", "updated_at": pd.Timestamp.now()
    }])
    
    snapshot = {
        "portfolio": df_port,
        "cash": df_cash,
        "trades": pd.DataFrame() # Vuoto
    }
    
    # 2. Save
    test_db.save_portfolio(snapshot)
    
    # 3. Load
    loaded = test_db.load_portfolio()
    
    # 4. Verify
    loaded_port = loaded["portfolio"]
    loaded_cash = loaded["cash"]
    
    assert not loaded_port.empty
    assert loaded_port.iloc[0]["ticker"] == "NVDA"
    assert loaded_port.iloc[0]["size"] == 5
    
    assert not loaded_cash.empty
    assert float(loaded_cash.iloc[0]["cash"]) == 12345.67