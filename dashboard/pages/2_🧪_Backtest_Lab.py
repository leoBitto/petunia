import streamlit as st
import pandas as pd
import json
import plotly.express as px
from pathlib import Path
import time

# Importiamo la funzione di backend
from services.backtest import run_backtest_session
from src.settings_manager import SettingsManager
from src.strategies import STRATEGY_MAP

st.set_page_config(page_title="Backtest Lab", layout="wide")
st.title("🧪 Backtest Laboratory")

# --- FUNZIONI DI SUPPORTO UI ---
def load_benchmark_data(session_path: Path):
    """Carica i dati di una sessione di backtest specifica."""
    data = {}
    summary_list = []
    
    if not session_path.exists():
        return {}, pd.DataFrame()

    for strat_dir in session_path.iterdir():
        if strat_dir.is_dir():
            strat_name = strat_dir.name
            eq_file = strat_dir / "equity_curve.csv"
            conf_file = strat_dir / "config.json"
            
            if eq_file.exists() and conf_file.exists():
                df_eq = pd.read_csv(eq_file)
                with open(conf_file, "r") as f:
                    conf = json.load(f)
                
                data[strat_name] = {
                    "equity": df_eq,
                    "config": conf,
                    "path": strat_dir
                }
                
                metrics = conf.get('metrics', {})
                trades_num = metrics.get('total_trades', conf.get('total_trades', 0))
                roi = metrics.get('roi_pct', 0.0)
                if 'roi_pct' not in metrics:
                    initial = conf.get('initial_capital', 1)
                    final = conf.get('final_equity', 1)
                    roi = ((final - initial) / initial) * 100

                summary_list.append({
                    "Strategy": strat_name,
                    "Final Equity": conf.get('final_equity', 0),
                    "ROI %": roi,
                    "Max DD %": metrics.get('max_drawdown_pct', 0.0),
                    "Fees Paid": metrics.get('total_fees', 0.0),
                    "Trades": trades_num,
                    "Params": str(conf.get('params', {}))
                })

    return data, pd.DataFrame(summary_list)

def plot_comparison(data_map):
    df_all = pd.DataFrame()
    for name, content in data_map.items():
        df = content['equity'].copy()
        df['Strategy'] = name
        df['date'] = pd.to_datetime(df['date'])
        df_all = pd.concat([df_all, df])
        
    if df_all.empty: return None
    
    fig = px.line(df_all, x='date', y='equity', color='Strategy', 
                  title="Equity Curve Comparison", markers=False)
    fig.update_layout(xaxis_title="Date", yaxis_title="Capital (€)", hovermode="x unified")
    return fig

# --- LAYOUT PRINCIPALE ---
tab_run, tab_results = st.tabs(["🚀 Run Simulation", "📊 Analyze Results"])

# ==========================================
# TAB 1: LANCIO BACKTEST
# ==========================================
with tab_run:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Configuration")
        
        # --- NOVITÀ: SELETTORE MODALITÀ ---
        run_mode = st.radio("Simulation Mode:", ["Single Strategy (Custom)", "Benchmark All (Batch)"], index=0)
        st.markdown("---")

        params = {}
        selected_strat = None

        if run_mode == "Single Strategy (Custom)":
            # 1. Selezione Strategia
            selected_strat = st.selectbox("Select Strategy:", list(STRATEGY_MAP.keys()))
            
            # 2. Parametri Custom
            st.write(" **Strategy Params:**")
            if selected_strat == "RSI":
                params['rsi_period'] = st.number_input("RSI Period", 1, 100, 14)
                params['rsi_lower'] = st.number_input("Lower Bound", 1, 49, 30)
                params['rsi_upper'] = st.number_input("Upper Bound", 51, 99, 70)
                params['atr_period'] = st.number_input("ATR Period", 1, 50, 14)
            elif selected_strat == "EMA":
                params['short_window'] = st.number_input("Fast EMA", 5, 100, 50)
                params['long_window'] = st.number_input("Slow EMA", 20, 365, 200)
                params['atr_period'] = st.number_input("ATR Period", 1, 50, 14)
        else:
            st.info("ℹ️ This will run ALL strategies defined in `strategies.json`.")

        st.markdown("---")
        # 3. Parametri Globali
        initial_cap = st.number_input("Initial Capital (€)", 1000, 1000000, 10000, step=1000)
        years = st.slider("History Depth (Years)", 1, 5, 2)
        
        if st.button("🔥 RUN SIMULATION", use_container_width=True):
            with st.spinner("Crunching numbers..."):
                try:
                    # Logica switch tra ALL e SINGLE
                    if run_mode == "Benchmark All (Batch)":
                        session_path = run_backtest_session(
                            mode="ALL",
                            initial_capital=initial_cap,
                            years=years
                        )
                    else:
                        session_path = run_backtest_session(
                            mode="SINGLE_OVERRIDE", 
                            override_strat_name=selected_strat, 
                            override_params=params, 
                            initial_capital=initial_cap,
                            years=years
                        )
                    
                    if session_path:
                        st.success("Simulation Complete!")
                        st.session_state['last_run_path'] = session_path
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Simulation failed. Check logs.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")

    with c2:
        st.info("👈 Choose 'Benchmark All' to compare multiple strategies from your config file.")

# ==========================================
# TAB 2: RISULTATI
# ==========================================
with tab_results:
    st.write("### 📂 Results Browser")
    
    base_dir = Path("data/backtests")
    if not base_dir.exists():
        st.warning("No backtests found yet.")
        st.stop()
        
    sessions = sorted([x.name for x in base_dir.iterdir() if x.is_dir()], reverse=True)
    
    default_idx = 0
    if 'last_run_path' in st.session_state:
        last_name = Path(st.session_state['last_run_path']).name
        if last_name in sessions:
            default_idx = sessions.index(last_name)

    selected_session = st.selectbox("Select Session (Timestamp)", sessions, index=default_idx)
    
    if selected_session:
        session_path = base_dir / selected_session
        strat_data, summary_df = load_benchmark_data(session_path)
        
        if not strat_data:
            st.warning("Invalid session.")
        else:
            st.subheader("🏆 Performance Matrix")
            st.dataframe(
                summary_df.style.format({
                    "Final Equity": "€ {:,.2f}",
                    "ROI %": "{:+.2f}%",
                    "Max DD %": "{:.2f}%",
                    "Fees Paid": "€ {:,.2f}"
                })
                .background_gradient(subset=["ROI %"], cmap="RdYlGn", vmin=-20, vmax=20)
                .background_gradient(subset=["Max DD %"], cmap="Reds"),
                use_container_width=True,
                hide_index=True
            )

            st.subheader("📈 Equity Curve")
            fig = plot_comparison(strat_data)
            if fig: st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔍 Deep Dive")
            
            col_sel_strat, _ = st.columns([1, 2])
            with col_sel_strat:
                detail_strat = st.selectbox("Inspect Strategy Details:", list(strat_data.keys()))
            
            if detail_strat:
                d_data = strat_data[detail_strat]
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.markdown("#### ⚙️ Config")
                    st.json(d_data['config'].get('params', {}))
                    st.write("**Fees & Risk:**")
                    st.json(d_data['config'].get('fees_config', {}))
                
                with c2:
                    st.markdown("#### 📜 Trades")
                    trades_csv = d_data['path'] / "trades.csv"
                    if trades_csv.exists():
                        df_trades = pd.read_csv(trades_csv)
                        st.dataframe(df_trades, height=300, use_container_width=True)