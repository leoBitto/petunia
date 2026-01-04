# dashboard/Home.py
import streamlit as st
import pandas as pd
from dashboard.utils import load_portfolio_data, load_ohlc_summary
from src.settings_manager import SettingsManager

st.set_page_config(page_title="Petunia Dashboard", page_icon="🌸", layout="wide")

st.title("🌸 Petunia | System Overview")

# --- 1. ACTIVE STRATEGY BADGE ---
try:
    settings = SettingsManager()
    active_strat = settings.get_active_strategy_name()
    
    # Usiamo un container colorato per evidenziare la strategia
    with st.container():
        c_badge, c_link = st.columns([3, 1])
        with c_badge:
            st.info(f"🧠 **Active Intelligence:** The system is currently running on **{active_strat}** strategy.")
        with c_link:
            # Purtroppo Streamlit non ha link interni facili, usiamo un testo guida
            st.caption("Change Strategy in:")
            st.page_link("pages/control_panel.py", label="🕹️ Control Panel", icon="🔧")
except Exception as e:
    st.error(f"⚠️ Error loading configuration: {e}")

st.markdown("---")

# 1. KPI Portafoglio
data = load_portfolio_data()
df_cash = data.get('cash', pd.DataFrame())
df_port = data.get('portfolio', pd.DataFrame())

col1, col2, col3, col4 = st.columns(4)

# Calcolo Totali
cash = float(df_cash.iloc[0]['cash']) if not df_cash.empty else 0.0
invested = (df_port['price'] * df_port['size']).sum() if not df_port.empty else 0.0
total_equity = cash + invested
active_tickers = len(df_port) if not df_port.empty else 0

col1.metric("Total Equity", f"€ {total_equity:,.2f}")
col2.metric("Cash Available", f"€ {cash:,.2f}")
col3.metric("Invested Capital", f"€ {invested:,.2f}")
col4.metric("Active Positions", f"{active_tickers}")

st.markdown("---")

# 2. Stato Sistema
st.subheader("📡 System Status")

# Tabella riassuntiva Ticker
df_ohlc = load_ohlc_summary()

c1, c2 = st.columns([2, 1])

with c1:
    if not df_ohlc.empty:
        # Ci assicuriamo che 'count' sia un intero
        df_ohlc['count'] = df_ohlc['count'].astype(int)
        
        st.dataframe(
            df_ohlc,
            column_config={
                "ticker": "Ticker",
                "last_date": "Last Update",
                "count": st.column_config.ProgressColumn(
                    "Data Points",
                    help="Numero di candele OHLC salvate",
                    format="%d",
                    min_value=0,
                    max_value=int(df_ohlc['count'].max())
                ),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nessun dato OHLC nel database.")

with c2:
    st.info("ℹ️ **Quick Actions**")
    if st.button("🔄 Refresh Data View"):
        st.rerun()
    
    st.markdown("Per operazioni di scrittura o log, vai al **Control Panel**.")