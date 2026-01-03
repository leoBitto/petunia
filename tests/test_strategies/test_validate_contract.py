import pandas as pd

# Definizione del Contratto
REQUIRED_COLUMNS = {'ticker', 'date', 'signal', 'atr', 'price', 'meta'}
VALID_SIGNALS = {'BUY', 'SELL', 'HOLD'}

def validate_strategy_output(df: pd.DataFrame):
    """
    Verifica che l'output della strategia rispetti rigorosamente il contratto
    richiesto dai moduli successivi (RiskManager, PortfolioManager).
    """
    # 1. Se vuoto (e.g. dati insufficienti), il contratto è rispettato (ritorna dataframe vuoto ma con colonne corrette o proprio vuoto)
    # Ma se la strategia restituisce righe, devono essere valide.
    if df.empty:
        # Controlliamo che abbia almeno le colonne se è vuoto (Best Practice)
        # Ma alcune implementazioni tornano None o DF vuoto senza colonne.
        # Per ora accettiamo DF vuoto.
        return True 

    # 2. Check Colonne Obbligatorie
    # Set difference: Colonne Richieste - Colonne Presenti
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing, f"VIOLAZIONE CONTRATTO. Colonne mancanti: {missing}"

    # 3. Check Integrità Dati
    # Signal deve essere stringa valida
    invalid_signals = df[~df['signal'].isin(VALID_SIGNALS)]
    assert invalid_signals.empty, f"Segnali non validi trovati: {invalid_signals['signal'].unique()}"
    
    # ATR deve essere positivo (fondamentale per Risk Manager)
    assert (df['atr'] > 0).all(), "Trovato ATR negativo o zero. Rischio di crash nel RiskManager."
    
    # Price deve essere positivo
    assert (df['price'] > 0).all(), "Trovato Prezzo negativo o zero."
    
    # Meta deve esistere
    assert 'meta' in df.columns