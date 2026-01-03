import pytest
from unittest.mock import patch, MagicMock
from src.drive_manager import DriveManager

# Mockiamo la catena di autenticazione per non richiedere il file JSON reale
@patch('src.drive_manager.Credentials.from_service_account_file')
@patch('src.drive_manager.gspread.authorize')
def test_get_universe_tickers(mock_auth, mock_creds):
    """Testa la lettura della lista ticker."""
    
    # Setup Mock Chain
    mock_client = MagicMock()
    mock_auth.return_value = mock_client
    
    mock_sheet = MagicMock()
    mock_client.open_by_key.return_value = mock_sheet
    
    # Simuliamo il foglio Universe (Header + Dati)
    fake_data = [
        ["Ticker", "Sector"], # Riga 0 Header
        ["AAPL", "Tech"],     # Riga 1
        ["MSFT", "Tech"],     # Riga 2
        ["", ""]              # Riga vuota sporca
    ]
    # sheet1 è la property che accede al primo foglio
    mock_sheet.sheet1.get_all_values.return_value = fake_data
    
    # Esecuzione
    dm = DriveManager()
    tickers = dm.get_universe_tickers()
    
    # Verifica
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "" not in tickers # Deve aver pulito la riga vuota
    assert len(tickers) == 2

@patch('src.drive_manager.Credentials.from_service_account_file')
@patch('src.drive_manager.gspread.authorize')
def test_get_pending_orders_cleaning(mock_auth, mock_creds):
    """Testa che i numeri vengano convertiti correttamente (stringa -> float)."""
    
    # Setup
    mock_client = mock_auth.return_value
    mock_sheet = mock_client.open_by_key.return_value
    mock_worksheet = MagicMock()
    # Qui mockiamo _get_worksheet interno o la catena open_by_key -> worksheet
    # Per semplicità, mockiamo la chiamata finale nel metodo _get_worksheet
    # Nota: dato che _get_worksheet usa client.open_by_key, il mock sopra funziona se configurato bene.
    # Ma nel test unitario, spesso è più facile mockare il metodo privato se complesso, o la libreria gspread.
    
    # Simuliamo get_all_records che restituisce lista di dizionari (come fa gspread)
    raw_orders = [
        {"ticker": "AAPL", "quantity": "10", "price": "150,50", "action": "BUY"}, # Nota la virgola
        {"ticker": "", "quantity": "", "price": ""} # Riga vuota
    ]
    
    # Dobbiamo intercettare la chiamata a worksheet("Orders")
    mock_sheet.worksheet.return_value.get_all_records.return_value = raw_orders
    
    dm = DriveManager()
    orders = dm.get_pending_orders()
    
    assert len(orders) == 1
    valid_order = orders[0]
    
    assert valid_order['ticker'] == "AAPL"
    assert valid_order['quantity'] == 10        # Deve essere INT
    assert valid_order['price'] == 150.50      # Deve essere FLOAT (virgola gestita)