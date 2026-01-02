import streamlit as st
import pandas as pd
from src.database_manager import DatabaseManager

# Configurazione Pagina
st.set_page_config(
    page_title="Petunia Dashboard",
    page_icon="🌸",
    layout="wide"
)

# Header
st.title("🌸 Petunia Trading System")
st.markdown("---")

# KPI Rapidi (Mockup - poi li collegheremo)
col1, col2, col3 = st.columns(3)
col1.metric("Status", "Online 🟢")
col2.metric("Active Strategies", "1")
col3.metric("Last Update", "Today")

# Test Connessione DB
st.subheader("🔌 Database Connection Check")

try:
    db = DatabaseManager()
    # Usiamo la funzione esistente per prendere un po' di dati
    tickers = db.get_ohlc_all_tickers(days=2) 
    st.success(f"Connesso! Trovati dati per {len(tickers)} ticker nel database.")
    
    with st.expander("Show Raw Data Preview"):
        st.write(tickers)
        
except Exception as e:
    st.error(f"Errore connessione DB: {e}")