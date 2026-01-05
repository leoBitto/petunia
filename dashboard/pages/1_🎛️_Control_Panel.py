import streamlit as st
import pandas as pd
import time
from pathlib import Path
from src.settings_manager import SettingsManager
from src.strategies import STRATEGY_MAP

st.set_page_config(page_title="Control Panel", layout="wide")
st.title("🎛️ System Control Panel")

# --- FUNZIONE LOG READER ---
def read_log_file(filename, lines=50):
    log_path = Path("logs") / filename
    if not log_path.exists():
        return [f"Log file {filename} not found."]
    try:
        with open(log_path, "r") as f:
            return f.readlines()[-lines:]
    except Exception as e:
        return [f"Error reading log: {e}"]

# --- TABS ---
# Aggiunto tab "System Logs"
tab_status, tab_strat, tab_data, tab_logs = st.tabs(["🟢 Status", "⚙️ Strategy & Risk", "💾 Data", "📜 System Logs"])

# --- TAB 1: STATUS ---
with tab_status:
    st.write("### System Health")
    st.info("System is Online. Docker containers are running.")

# --- TAB 2: STRATEGY ---
with tab_strat:
    st.subheader("⚙️ Configuration")
    try:
        manager = SettingsManager()
        config = manager.load_config()
    except Exception as e:
        st.error(f"Errore caricamento configurazione: {e}")
        st.stop()

    c_strat, c_risk, c_fees = st.columns([1.2, 1, 1])

    with c_strat:
        with st.container(border=True):
            st.write("#### 🎯 Strategy")
            current_active = config.get("active_strategy", "RSI")
            available = list(STRATEGY_MAP.keys())
            new_active = st.radio("Active:", available, index=available.index(current_active) if current_active in available else 0)
            
            st.markdown("---")
            current_strat_params = config.get("strategies_params", {}).get(new_active, {})
            
            with st.form(key="strat_form"):
                updated_strat = {}
                if new_active == "RSI":
                    updated_strat['rsi_period'] = st.number_input("RSI Period", value=int(current_strat_params.get('rsi_period', 14)))
                    updated_strat['rsi_lower'] = st.number_input("Lower", value=int(current_strat_params.get('rsi_lower', 30)))
                    updated_strat['rsi_upper'] = st.number_input("Upper", value=int(current_strat_params.get('rsi_upper', 70)))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=int(current_strat_params.get('atr_period', 14)))
                elif new_active == "EMA":
                    updated_strat['short_window'] = st.number_input("Fast EMA", value=int(current_strat_params.get('short_window', 50)))
                    updated_strat['long_window'] = st.number_input("Slow EMA", value=int(current_strat_params.get('long_window', 200)))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=int(current_strat_params.get('atr_period', 14)))
                
                if st.form_submit_button("💾 Save Strategy"):
                    config["active_strategy"] = new_active
                    if "strategies_params" not in config: config["strategies_params"] = {}
                    config["strategies_params"][new_active] = updated_strat
                    manager.save_config(config)
                    st.success("Saved!")
                    time.sleep(1)
                    st.rerun()

    with c_risk:
        with st.container(border=True):
            st.write("#### ⚖️ Risk")
            current_risk = config.get("risk_params", {})
            with st.form(key="risk_form"):
                def_risk = current_risk.get("risk_per_trade", 0.02)
                def_stop = current_risk.get("stop_atr_multiplier", 2.0)
                new_risk = st.number_input("Risk %", 0.01, 0.20, float(def_risk), 0.01)
                new_stop = st.number_input("Stop (xATR)", 1.0, 5.0, float(def_stop), 0.1)
                if st.form_submit_button("💾 Save Risk"):
                    config["risk_params"] = {"risk_per_trade": new_risk, "stop_atr_multiplier": new_stop}
                    manager.save_config(config)
                    st.success("Saved!")
                    time.sleep(1)
                    st.rerun()

    with c_fees:
        with st.container(border=True):
            st.write("#### 💸 Fees")
            current_fees = config.get("fees_config", {})
            with st.form(key="fees_form"):
                def_fix = current_fees.get("fixed_euro", 0.0)
                def_pct = current_fees.get("percentage", 0.0)
                new_fix = st.number_input("Fixed (€)", 0.0, value=float(def_fix), step=0.5)
                new_pct = st.number_input("Var (%)", 0.0, 1.0, float(def_pct), 0.0001, format="%.4f")
                if st.form_submit_button("💾 Save Fees"):
                    config["fees_config"] = {"fixed_euro": new_fix, "percentage": new_pct}
                    manager.save_config(config)
                    st.success("Saved!")
                    time.sleep(1)
                    st.rerun()

# --- TAB 3: DATA ---
with tab_data:
    st.write("### Data Management")
    st.info("Manual data fetch coming soon.")

# --- TAB 4: LOGS (RIPRISTINATO) ---
with tab_logs:
    st.subheader("📜 System Log Inspector")
    c_sel, c_refresh = st.columns([3, 1])
    with c_sel:
        log_file = st.selectbox("Select Log File:", ["Backtester.log", "WeeklyRun.log", "DailyRun.log"])
    with c_refresh:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh"):
            st.rerun()
    
    lines = read_log_file(log_file)
    with st.container(height=500, border=True):
        st.code("".join(lines), language="text")