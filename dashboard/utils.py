# dashboard/utils.py
import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager
from src.portfolio_manager import PortfolioManager

@st.cache_resource
def get_db():
    """Restituisce una istanza del DB Manager (cacheata)."""
    return DatabaseManager()

def load_portfolio_data():
    """Carica i dati senza cache (devono essere freschi)."""
    db = get_db()
    return db.load_portfolio()

@st.cache_data(ttl=60) # Cache valida per 60 secondi
def load_ohlc_summary():
    """Conta quanti dati abbiamo per ticker."""
    db = get_db()
    # Query leggera per contare le righe
    query = "SELECT ticker, COUNT(*) as count, MAX(date) as last_date FROM ohlc GROUP BY ticker"
    rows = db.query(query)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)