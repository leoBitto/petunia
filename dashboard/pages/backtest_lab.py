import streamlit as st
import pandas as pd
from pathlib import Path
import json
from services.backtest import run_backtest # Importiamo la funzione backend

st.set_page_config(page_title="Backtest Lab", page_icon="🧪", layout="wide")

st.title("🧪 Backtest Laboratory")

# Sidebar: Configurazione
with st.sidebar:
    st.header("⚙️ Configuration")
    
    strategy = st.selectbox("Strategy", ["RSI", "MACD (Coming Soon)"])
    
    st.subheader("Parameters")
    initial_cap = st.number_input("Initial Capital (€)", value=10000, step=1000)
    years = st.slider("Years History", 1, 5, 2)
    
    # Parametri Dinamici per RSI
    params = {}
    if strategy == "RSI":
        params['rsi_period'] = st.slider("RSI Period", 5, 30, 14)
        params['rsi_lower'] = st.slider("Oversold (<)", 10, 45, 30)
        params['rsi_upper'] = st.slider("Overbought (>)", 55, 90, 70)
        params['atr_period'] = st.slider("ATR Period", 5, 30, 14)
    
    run_btn = st.button("🚀 RUN BACKTEST", type="primary")

# Main Area
tab_run, tab_history = st.tabs(["Current Run", "History Archive"])

with tab_run:
    if run_btn:
        with st.spinner("Running simulation... (This may take a moment)"):
            try:
                # Eseguiamo il backtest
                result_path = run_backtest(
                    strategy_name=strategy,
                    initial_capital=initial_cap,
                    days_history=years*365,
                    strategy_params=params
                )
                st.success(f"Simulation completed! Saved in: {result_path}")
                
                # Visualizzazione Rapida Risultati
                p = Path(result_path)
                
                # Immagine
                if (p / "chart.png").exists():
                    # CORRETTO: use_container_width invece di width
                    st.image(str(p / "chart.png"), use_container_width=True)
                
                # Metriche da JSON
                if (p / "config.json").exists():
                    with open(p / "config.json") as f:
                        res = json.load(f)
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Final Equity", f"€ {res.get('final_equity', 0):,.2f}")
                    m2.metric("Total Trades", res.get('total_trades', 0))
                    # Calcolo ROI al volo
                    roi = ((res.get('final_equity', 0) - initial_cap) / initial_cap) * 100
                    m3.metric("Total ROI", f"{roi:+.2f}%")
                    
            except Exception as e:
                st.error(f"Errore durante il backtest: {e}")

with tab_history:
    st.write("📂 **Previous Runs Browser**")
    base_dir = Path("data/backtests")
    
    if base_dir.exists():
        # Logica per esplorare le cartelle
        strategies = [x.name for x in base_dir.iterdir() if x.is_dir()]
        
        # --- LAYOUT A COLONNE PER I SELETTORI ---
        c_strat, c_run = st.columns(2)
        
        with c_strat:
            sel_strat = st.selectbox("Select Strategy Folder", strategies)
        
        sel_run = None
        if sel_strat:
            with c_run:
                # Controllo se la cartella esiste e non è vuota
                strat_path = base_dir / sel_strat
                if strat_path.exists():
                     runs = sorted([x.name for x in strat_path.iterdir()], reverse=True)
                     sel_run = st.selectbox("Select Timestamp", runs)
            
            if sel_run:
                run_path = base_dir / sel_strat / sel_run
                st.caption(f"Path: {run_path}")
                st.markdown("---")
                
                # Visualizzazione Dati
                col_img, col_data = st.columns([1, 1])
                
                with col_img:
                    if (run_path / "chart.png").exists():
                        # CORRETTO: use_container_width
                        st.image(str(run_path / "chart.png"), use_container_width=True)
                
                with col_data:
                    if (run_path / "config.json").exists():
                        with open(run_path / "config.json") as f:
                            conf = json.load(f)
                        st.json(conf, expanded=False)

                    if (run_path / "trades.csv").exists():
                        # CORRETTO: use_container_width e height numerico
                        st.dataframe(pd.read_csv(run_path / "trades.csv"), use_container_width=True, height=300)