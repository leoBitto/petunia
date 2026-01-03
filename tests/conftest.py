import pytest
import pandas as pd
import numpy as np
from src.database_manager import DatabaseManager


# --- GENERATORE DATI STANDARD ---
def generate_market_data(trend_type, length=300, start_price=100, volatility=0.02):
    """
    Genera dati OHLCV coerenti matematicamente.
    Date: Termina OGGI e va indietro di 'length' giorni.
    """
    # MODIFICA: Generazione date dinamica (fino a oggi)
    end_date = pd.Timestamp.now().normalize() # normalize mette l'ora a 00:00:00
    dates = pd.date_range(end=end_date, periods=length)
    
    # Base trend
    x = np.linspace(0, 10, length)
    noise = np.random.normal(0, start_price * (volatility/5), length) # Un po' di rumore casuale
    
    if trend_type == "UP":
        # Salita lineare + rumore
        closes = np.linspace(start_price, start_price * 2, length) + noise
    elif trend_type == "DOWN":
        # Discesa lineare + rumore
        closes = np.linspace(start_price * 2, start_price, length) + noise
    elif trend_type == "SIDEWAYS":
        # Sinusoide + rumore
        closes = start_price + (np.sin(x) * (start_price * 0.05)) + noise
    
    # Deriviamo OHLC coerenti
    opens = closes + np.random.normal(0, start_price * 0.005, length)
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, volatility, length)))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, volatility, length)))
    volume = np.random.randint(1000, 50000, length)

    df = pd.DataFrame({
        'date': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volume
    })
    
    return {"TEST_TICKER": df}

# --- FIXTURES ---
@pytest.fixture
def market_uptrend():
    return generate_market_data("UP")

@pytest.fixture
def market_downtrend():
    return generate_market_data("DOWN")

@pytest.fixture
def market_sideways():
    return generate_market_data("SIDEWAYS")
    

@pytest.fixture(scope="function")
def test_db():
    """
    Crea un'istanza reale del DB Manager collegata al container Postgres.
    PATTERN: Setup -> Yield -> Teardown
    """
    # 1. SETUP: Connessione e Creazione Tabelle Pulite
    db = DatabaseManager()
    db.drop_schema()  # Pulizia preventiva (tabula rasa)
    db.init_schema()  # Creazione tabelle vuote
    
    yield db  # Qui passa il controllo al test che userà 'db'
    
    # 2. TEARDOWN: Pulizia finale
    # Opzionale: se vuoi lasciare i dati per ispezionarli post-fallimento, commenta questa riga
    db.drop_schema() 
    db.close()