import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils import load_portfolio_data

st.set_page_config(page_title="Portfolio Monitor", page_icon="📈", layout="wide")

st.title("📈 Portfolio Monitor")

# 1. Caricamento Dati
data = load_portfolio_data()
df_port = data.get('portfolio', pd.DataFrame())
df_cash = data.get('cash', pd.DataFrame())
df_trades = data.get('trades', pd.DataFrame())

# Gestione caso vuoto
cash_val = float(df_cash.iloc[0]['cash']) if not df_cash.empty else 0.0
currency = df_cash.iloc[0]['currency'] if not df_cash.empty else "EUR"

# Calcolo valore investito
invested_val = 0.0
if not df_port.empty:
    # Valore attuale approssimato (usiamo 'price' che è l'ultimo prezzo salvato nel DB)
    # In un sistema real-time qui dovremmo fare una fetch dei prezzi live
    df_port['current_value'] = df_port['size'] * df_port['price']
    invested_val = df_port['current_value'].sum()

total_equity = cash_val + invested_val

# 2. KPI Principali
col1, col2, col3 = st.columns(3)
col1.metric("Total Equity", f"€ {total_equity:,.2f}")
col2.metric("Cash Available", f"€ {cash_val:,.2f}")
col3.metric("Invested Assets", f"€ {invested_val:,.2f}")

st.markdown("---")

# 3. Composizione Portafoglio (Layout a 2 colonne)
c_chart, c_table = st.columns([1, 2])

with c_chart:
    st.subheader("Asset Allocation")
    # Prepariamo dati per il grafico a torta
    labels = ['Cash']
    values = [cash_val]
    
    if not df_port.empty:
        labels.extend(df_port['ticker'].tolist())
        values.extend(df_port['current_value'].tolist())
    
    # Grafico Interattivo con Plotly
    fig = px.pie(names=labels, values=values, hole=0.4)
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

with c_table:
    st.subheader("Current Positions")
    if not df_port.empty:
        # Formattiamo la tabella per renderla leggibile
        display_df = df_port[['ticker', 'size', 'price', 'current_value', 'stop_loss', 'updated_at']].copy()
        display_df.columns = ['Ticker', 'Qty', 'Last Price', 'Total Value', 'Stop Loss', 'Last Update']
        
        st.dataframe(
            display_df.style.format({
                "Last Price": "€ {:.2f}",
                "Total Value": "€ {:.2f}",
                "Stop Loss": "€ {:.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Portafoglio vuoto (100% Cash).")

st.markdown("---")

# 4. Storico Operazioni (Trade History)
st.subheader("📜 Trade History")
if not df_trades.empty:
    # Ordiniamo per data decrescente
    df_trades['date'] = pd.to_datetime(df_trades['date'])
    df_trades = df_trades.sort_values('date', ascending=False)
    
    # Coloriamo le azioni (BUY=Verde, SELL=Rosso)
    def color_action(val):
        color = '#d4edda' if val == 'BUY' else '#f8d7da' # Colori pastello verde/rosso
        return f'background-color: {color}'

    st.dataframe(
        df_trades.style.applymap(color_action, subset=['action'])
                 .format({"price": "€ {:.2f}"}),
        use_container_width=True,
        hide_index=True
    )
else:
    st.write("Nessuna operazione registrata nello storico.")