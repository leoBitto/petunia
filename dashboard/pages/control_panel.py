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
    st.subheader("⚙️ Algorithmic Rules")
    
    # 1. Caricamento Config
    try:
        manager = SettingsManager()
        config = manager.load_config()
    except Exception as e:
        st.error(f"Errore caricamento configurazione: {e}")
        st.stop()

    c_active, c_params = st.columns([1, 2])

    # --- SELEZIONE STRATEGIA ---
    with c_active:
        with st.container(border=True):
            st.write("#### 🎯 Active Strategy")
            st.caption("Questa strategia verrà eseguita al prossimo Weekly Run.")
            
            current_active = config.get("active_strategy", "RSI")
            available_strategies = list(STRATEGY_MAP.keys())
            
            new_active = st.radio(
                "Seleziona Motore:",
                available_strategies,
                index=available_strategies.index(current_active) if current_active in available_strategies else 0
            )
            
            if new_active != current_active:
                if st.button("💾 Save Active Strategy"):
                    config["active_strategy"] = new_active
                    manager.save_config(config)
                    st.success(f"Strategia attiva impostata su: **{new_active}**")
                    time.sleep(1)
                    st.rerun()

    # --- PARAMETRI STRATEGIA ---
    with c_params:
        with st.container(border=True):
            st.write(f"#### 🔧 Parameters: {new_active}")
            
            current_params = config.get("strategies_params", {}).get(new_active, {})
            
            with st.form(key="strategy_params_form"):
                updated_params = {}
                
                # UI Dinamica in base alla strategia
                if new_active == "RSI":
                    k1, k2 = st.columns(2)
                    with k1:
                        updated_params['rsi_period'] = st.number_input("RSI Period", value=current_params.get('rsi_period', 14))
                        updated_params['atr_period'] = st.number_input("ATR Period", value=current_params.get('atr_period', 14))
                    with k2:
                        updated_params['rsi_lower'] = st.slider("Oversold (<)", 10, 45, current_params.get('rsi_lower', 30))
                        updated_params['rsi_upper'] = st.slider("Overbought (>)", 55, 90, current_params.get('rsi_upper', 70))

                elif new_active == "EMA":
                    k1, k2 = st.columns(2)
                    with k1:
                        updated_params['short_window'] = st.number_input("Fast EMA", value=current_params.get('short_window', 50))
                        updated_params['atr_period'] = st.number_input("ATR Period", value=current_params.get('atr_period', 14))
                    with k2:
                        updated_params['long_window'] = st.number_input("Slow EMA", value=current_params.get('long_window', 200))
                
                else:
                    st.warning("UI non disponibile per questa strategia. Usa JSON raw.")
                    # Fallback generico: mostriamo il JSON editabile come testo? Per ora manteniamo i vecchi valori
                    updated_params = current_params

                submit = st.form_submit_button("💾 Update Parameters")
                
                if submit:
                    if "strategies_params" not in config:
                        config["strategies_params"] = {}
                    config["strategies_params"][new_active] = updated_params
                    manager.save_config(config)
                    st.success("Parametri salvati!")
                    time.sleep(1)
                    st.rerun()

    with st.expander("🔍 View Raw JSON"):
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