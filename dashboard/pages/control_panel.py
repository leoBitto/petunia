import streamlit as st
from pathlib import Path
import time
import json

# Import Core Services
from src.yfinance_manager import YFinanceManager
from src.database_manager import DatabaseManager
from src.drive_manager import DriveManager
from src.settings_manager import SettingsManager
from src.strategies import STRATEGY_MAP

st.set_page_config(page_title="Control Panel", page_icon="🕹️", layout="wide")

st.title("🕹️ Control Panel")
st.markdown("Gestione centralizzata del sistema: Dati, Strategie e Log.")

# Creiamo 3 Tab per organizzare le funzionalità
tab_ops, tab_strat, tab_logs = st.tabs(["🛠️ System Operations", "🧠 Strategy Config", "📜 System Logs"])

# ==============================================================================
# TAB 1: SYSTEM OPERATIONS (Data Fetch, DB Reset)
# ==============================================================================
with tab_ops:
    col_fetch, col_danger = st.columns(2)
    
    with col_fetch:
        st.subheader("📥 Data Ingestion")
        with st.container(border=True):
            st.write("**Fetch Historical Data**")
            st.caption("Scarica dati da Yahoo Finance e popola il DB.")
            
            years_to_fetch = st.number_input("Years of History", min_value=1, max_value=10, value=1)
            
            if st.button("🚀 Start Data Fetch", type="primary"):
                status_container = st.status("Avvio procedura di download...", expanded=True)
                try:
                    status_container.write("Lettura Universe da Google Sheets...")
                    drive = DriveManager()
                    tickers = drive.get_universe_tickers()
                    
                    if not tickers:
                        status_container.error("Nessun ticker trovato nel foglio 'Universe'!")
                    else:
                        status_container.write(f"Trovati {len(tickers)} ticker.")
                        
                        status_container.write(f"Download di {years_to_fetch} anni di storico...")
                        yf = YFinanceManager()
                        data = yf.fetch_history(tickers, years=years_to_fetch)
                        
                        if data:
                            status_container.write(f"Salvataggio di {len(data)} righe nel Database...")
                            db = DatabaseManager()
                            db.upsert_ohlc(data)
                            
                            status_container.update(label="✅ Operazione completata!", state="complete", expanded=False)
                            st.success(f"Database aggiornato con {len(data)} nuovi record!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            status_container.error("Nessun dato ricevuto da Yahoo Finance.")
                except Exception as e:
                    status_container.error(f"Errore critico: {e}")

    with col_danger:
        st.subheader("⚠️ Danger Zone")
        with st.container(border=True):
            st.write("**Reset Database**")
            st.caption("Cancella e ricrea lo schema del DB. Perdi tutti i dati storici.")
            if st.button("🗑️ Reset Schema", type="secondary"):
                if st.checkbox("Confermo la cancellazione totale"):
                    db = DatabaseManager()
                    db.drop_schema()
                    db.init_schema()
                    st.warning("Database resettato con successo.")

# ==============================================================================
# TAB 2: STRATEGY CONFIGURATION (JSON Manager)
# ==============================================================================
with tab_strat:
    st.subheader("⚙️ Algorithmic & Risk Rules")
    
    try:
        manager = SettingsManager()
        config = manager.load_config()
    except Exception as e:
        st.error(f"Errore caricamento configurazione: {e}")
        st.stop()

    # Layout a 3 Colonne: Strategia Attiva | Parametri Strategia | Parametri Rischio
    c_active, c_strat_params, c_risk_params = st.columns([1, 1.5, 1.5])

    # 1. STRATEGIA ATTIVA
    with c_active:
        with st.container(border=True):
            st.write("#### 🎯 Active Engine")
            current_active = config.get("active_strategy", "RSI")
            available = list(STRATEGY_MAP.keys())
            
            new_active = st.radio("Strategy:", available, index=available.index(current_active) if current_active in available else 0)
            
            if new_active != current_active:
                if st.button("💾 Set Active"):
                    config["active_strategy"] = new_active
                    manager.save_config(config)
                    st.success(f"Attiva: {new_active}")
                    time.sleep(1)
                    st.rerun()

    # 2. PARAMETRI STRATEGIA
    with c_strat_params:
        with st.container(border=True):
            st.write(f"#### 📊 {new_active} Settings")
            current_strat_params = config.get("strategies_params", {}).get(new_active, {})
            
            with st.form(key="strat_form"):
                updated_strat = {}
                if new_active == "RSI":
                    updated_strat['rsi_period'] = st.number_input("RSI Period", value=current_strat_params.get('rsi_period', 14))
                    updated_strat['rsi_lower'] = st.number_input("Lower (<)", value=current_strat_params.get('rsi_lower', 30))
                    updated_strat['rsi_upper'] = st.number_input("Upper (>)", value=current_strat_params.get('rsi_upper', 70))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=current_strat_params.get('atr_period', 14))
                elif new_active == "EMA":
                    updated_strat['short_window'] = st.number_input("Fast EMA", value=current_strat_params.get('short_window', 50))
                    updated_strat['long_window'] = st.number_input("Slow EMA", value=current_strat_params.get('long_window', 200))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=current_strat_params.get('atr_period', 14))
                
                if st.form_submit_button("💾 Save Strategy Params"):
                    if "strategies_params" not in config: config["strategies_params"] = {}
                    config["strategies_params"][new_active] = updated_strat
                    manager.save_config(config)
                    st.success("Strategy Saved!")
                    time.sleep(1)
                    st.rerun()

    # 3. PARAMETRI RISCHIO (NUOVO!)
    with c_risk_params:
        with st.container(border=True):
            st.write("#### ⚖️ Risk Management")
            current_risk = config.get("risk_params", {})
            
            with st.form(key="risk_form"):
                # Valori di default di visualizzazione se il json è vuoto
                def_risk_trade = current_risk.get("risk_per_trade", 0.02)
                def_stop_atr = current_risk.get("stop_atr_multiplier", 2.0)
                
                # Input
                new_risk_trade = st.number_input("Risk per Trade (%)", min_value=0.01, max_value=0.20, value=float(def_risk_trade), step=0.01, format="%.2f")
                new_stop_atr = st.number_input("Stop Loss (x ATR)", min_value=0.5, max_value=5.0, value=float(def_stop_atr), step=0.1)
                
                if st.form_submit_button("💾 Save Risk Params"):
                    config["risk_params"] = {
                        "risk_per_trade": new_risk_trade,
                        "stop_atr_multiplier": new_stop_atr
                    }
                    manager.save_config(config)
                    st.success("Risk Params Saved!")
                    time.sleep(1)
                    st.rerun()

    with st.expander("🔍 Raw JSON Config"):
        st.json(config)
# ==============================================================================
# TAB 3: SYSTEM LOGS
# ==============================================================================
with tab_logs:
    st.subheader("📜 System Inspector")
    
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = [f.name for f in log_dir.glob("*.log")]
        
        if log_files:
            col_sel, col_view = st.columns([1, 4])
            
            with col_sel:
                selected_file = st.selectbox("Log File:", log_files, index=0)
                lines_count = st.slider("Lines:", 10, 500, 50)
                if st.button("🔄 Refresh"):
                    st.rerun()
            
            with col_view:
                log_path = log_dir / selected_file
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()[-lines_count:]
                    st.code("".join(lines), language="log")
                except Exception as e:
                    st.error(f"Errore lettura log: {e}")
        else:
            st.info("Nessun file di log trovato.")
    else:
        st.error("Cartella logs non trovata.")