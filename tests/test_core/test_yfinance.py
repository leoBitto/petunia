import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.yfinance_manager import YFinanceManager

@patch('src.yfinance_manager.yf.download')
def test_fetch_ohlc_success(mock_download):
    """
    Testa che i dati grezzi di yfinance vengano normalizzati correttamente.
    """
    # 1. MOCK DATA (Simuliamo la risposta brutta di yfinance)
    # yfinance spesso restituisce MultiIndex se scarichi più ticker, o Index semplice se uno solo.
    # Simuliamo caso semplice.
    data = {
        'Open': [100.0], 'High': [105.0], 'Low': [95.0], 'Close': [102.0], 'Volume': [1000]
    }
    mock_df = pd.DataFrame(data, index=pd.to_datetime(["2024-01-01"]))
    # Aggiungiamo Ticker come colonna o indice a seconda di come yfinance si comporta quel giorno
    # Nel codice YFinanceManager gestiamo entrambi, qui simuliamo il reset_index
    mock_df['Ticker'] = "AAPL" 
    
    mock_download.return_value = mock_df

    # 2. ESECUZIONE
    yf = YFinanceManager()
    result = yf.fetch_ohlc(["AAPL"], days=5)

    # 3. VERIFICA
    assert len(result) == 1
    row = result[0]
    
    # La tupla deve essere: (Ticker, Date, Open, High, Low, Close, Volume)
    assert row[0] == "AAPL"
    assert row[3] == 105.0 # High
    assert row[6] == 1000  # Volume

@patch('src.yfinance_manager.yf.download')
def test_fetch_ohlc_empty(mock_download):
    """Testa la gestione di nessun dato."""
    mock_download.return_value = pd.DataFrame()
    
    yf = YFinanceManager()
    result = yf.fetch_ohlc(["AAPL"])
    
    assert result == []