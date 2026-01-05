import streamlit as st
import pandas as pd
import time
from src.settings_manager import SettingsManager
from src.strategies import STRATEGY_MAP

st.set_page_config(page_title="Control Panel", layout="wide")
st.title("🎛️ System Control Panel")

# Tabs principali
tab_status, tab_strat, tab_data = st.tabs(["🟢 System Status", "⚙️ Strategy & Risk", "💾 Data Management"])

# --- TAB 1: STATUS ---
with tab_status:
    st.write("### System Health")
    st.info("System is Online. Docker containers are running.")

# --- TAB 2: STRATEGY & RISK & FEES ---
with tab_strat:
    st.subheader("⚙️ Algorithmic Configuration")
    
    try:
        manager = SettingsManager()
        config = manager.load_config()
    except Exception as e:
        st.error(f"Errore caricamento configurazione: {e}")
        st.stop()

    # Layout a 3 Colonne: Strategia | Rischio | Commissioni
    c_strat, c_risk, c_fees = st.columns([1.2, 1, 1])

    # ---------------------------------------------------------
    # COLONNA 1: STRATEGIA (RSI, EMA, etc.)
    # ---------------------------------------------------------
    with c_strat:
        with st.container(border=True):
            st.write("#### 🎯 Strategy Engine")
            
            # Selezione Strategia Attiva
            current_active = config.get("active_strategy", "RSI")
            available = list(STRATEGY_MAP.keys())
            new_active = st.radio("Active Strategy:", available, index=available.index(current_active) if current_active in available else 0)
            
            st.markdown("---")
            st.write(f"**{new_active} Parameters:**")
            
            # Form Parametri Strategia
            current_strat_params = config.get("strategies_params", {}).get(new_active, {})
            
            # Qui costruiamo dinamicamente i campi in base alla strategia scelta
            with st.form(key="strat_form"):
                updated_strat = {}
                
                if new_active == "RSI":
                    updated_strat['rsi_period'] = st.number_input("RSI Period", value=int(current_strat_params.get('rsi_period', 14)))
                    updated_strat['rsi_lower'] = st.number_input("Lower (<)", value=int(current_strat_params.get('rsi_lower', 30)))
                    updated_strat['rsi_upper'] = st.number_input("Upper (>)", value=int(current_strat_params.get('rsi_upper', 70)))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=int(current_strat_params.get('atr_period', 14)))
                
                elif new_active == "EMA":
                    updated_strat['short_window'] = st.number_input("Fast EMA", value=int(current_strat_params.get('short_window', 50)))
                    updated_strat['long_window'] = st.number_input("Slow EMA", value=int(current_strat_params.get('long_window', 200)))
                    updated_strat['atr_period'] = st.number_input("ATR Period", value=int(current_strat_params.get('atr_period', 14)))
                
                if st.form_submit_button("💾 Save Strategy"):
                    # Salviamo sia l'attiva che i parametri
                    config["active_strategy"] = new_active
                    if "strategies_params" not in config: config["strategies_params"] = {}
                    config["strategies_params"][new_active] = updated_strat
                    
                    manager.save_config(config)
                    st.success("Strategy Updated!")
                    time.sleep(1)
                    st.rerun()

    # ---------------------------------------------------------
    # COLONNA 2: RISCHIO (Money Management)
    # ---------------------------------------------------------
    with c_risk:
        with st.container(border=True):
            st.write("#### ⚖️ Risk Rules")
            current_risk = config.get("risk_params", {})
            
            with st.form(key="risk_form"):
                # Default values
                def_risk = current_risk.get("risk_per_trade", 0.02)
                def_stop = current_risk.get("stop_atr_multiplier", 2.0)
                
                new_risk = st.number_input("Risk % per Trade", min_value=0.01, max_value=0.20, value=float(def_risk), step=0.01, format="%.2f")
                new_stop = st.number_input("Stop Loss (x ATR)", min_value=1.0, max_value=5.0, value=float(def_stop), step=0.1)
                
                if st.form_submit_button("💾 Save Risk Rules"):
                    config["risk_params"] = {
                        "risk_per_trade": new_risk,
                        "stop_atr_multiplier": new_stop
                    }
                    manager.save_config(config)
                    st.success("Risk Rules Saved!")
                    time.sleep(1)
                    st.rerun()

    # ---------------------------------------------------------
    # COLONNA 3: COSTI (Commissioni Broker)
    # ---------------------------------------------------------
    with c_fees:
        with st.container(border=True):
            st.write("#### 💸 Fees & Costs")
            current_fees = config.get("fees_config", {})
            
            with st.form(key="fees_form"):
                # Default values (0 se non esistono)
                def_fix = current_fees.get("fixed_euro", 0.0)
                def_pct = current_fees.get("percentage", 0.0)
                
                new_fix = st.number_input("Fixed Fee (€)", min_value=0.0, value=float(def_fix), step=0.5)
                new_pct = st.number_input("Variable Fee (%)", min_value=0.0, max_value=1.0, value=float(def_pct), step=0.0001, format="%.4f")
                
                st.caption("Es. Degiro Italia: ~1.00€ + 0%")
                st.caption("Es. Banca Tradizionale: ~5.00€ + 0.19%")

                if st.form_submit_button("💾 Save Fees"):
                    config["fees_config"] = {
                        "fixed_euro": new_fix,
                        "percentage": new_pct
                    }
                    manager.save_config(config)
                    st.success("Fees Config Saved!")
                    time.sleep(1)
                    st.rerun()

    # Debug JSON
    with st.expander("🔍 View Raw Config JSON"):
        st.json(config)

# --- TAB 3: DATA (Placeholder per download) ---
with tab_data:
    st.write("### Data Management")
    st.write("Use this section to trigger manual downloads (implemented in daily_run).")
    if st.button("📥 Force Fetch Data (Last 3 Years)"):
        st.info("Feature coming soon via manual trigger...")