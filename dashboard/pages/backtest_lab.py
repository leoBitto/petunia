import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json

# IMPORT DIRETTO DEL SERVIZIO BACKEND
from services.backtest import run_backtest_session 
from src.strategies import STRATEGY_MAP
from src.settings_manager import SettingsManager

st.set_page_config(page_title="Backtest Lab", page_icon="🧪", layout="wide")
st.title("🧪 Backtest Laboratory")

# --- HELPER FUNCTIONS ---

def load_benchmark_data(session_path: Path):
    """
    Scansiona una cartella di sessione (TIMESTAMP) e carica i dati di tutte le strategie trovate.
    Ritorna:
      - strategies_data: dict { 'StrategyName': {'equity': df, 'config': dict, 'path': Path} }
      - comparison_df: DataFrame riassuntivo per la tabella
    """
    strategies_data = {}
    summary_list = []
    
    # Cerca tutte le sottocartelle (ogni sottocartella è una strategia)
    subdirs = [x for x in session_path.iterdir() if x.is_dir()]
    
    for strat_dir in subdirs:
        strat_name = strat_dir.name
        
        # Carica Equity Curve
        eq_path = strat_dir / "equity_curve.csv"
        conf_path = strat_dir / "config.json"
        
        if eq_path.exists() and conf_path.exists():
            df_eq = pd.read_csv(eq_path)
            df_eq['date'] = pd.to_datetime(df_eq['date'])
            
            with open(conf_path) as f:
                conf = json.load(f)
                
            strategies_data[strat_name] = {
                "equity": df_eq,
                "config": conf,
                "path": strat_dir
            }
            
            # Dati per la tabella riassuntiva
            initial = conf.get('initial_capital', 0)
            final = conf.get('final_equity', 0)
            roi = ((final - initial) / initial) * 100 if initial > 0 else 0
            
            summary_list.append({
                "Strategy": strat_name,
                "Final Equity": final,
                "ROI %": roi,
                "Trades": conf.get('total_trades', 0),
                "Params": str(conf.get('params', {}))
            })
            
    return strategies_data, pd.DataFrame(summary_list)

def plot_comparison(strategies_data):
    """Genera un grafico Plotly unificato."""
    fig = go.Figure()
    
    for name, data in strategies_data.items():
        df = data['equity']
        if not df.empty:
            fig.add_trace(go.Scatter(
                x=df['date'], 
                y=df['equity'],
                mode='lines',
                name=name
            ))
            
    fig.update_layout(
        title="Equity Curve Comparison",
        xaxis_title="Date",
        yaxis_title="Capital (€)",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right")
    )
    return fig

# --- SIDEBAR CONFIGURATION ---

with st.sidebar:
    st.header("⚙️ Configuration")
    
    mode = st.radio("Run Mode", ["Single Strategy", "Benchmark (Run All)"])
    
    # Carica parametri salvati per pre-compilare i campi
    try:
        manager = SettingsManager()
        saved_config = manager.load_config()
    except:
        saved_config = {}

    selected_strat = None
    params = {}
    
    if mode == "Single Strategy":
        selected_strat = st.selectbox("Select Strategy", list(STRATEGY_MAP.keys()))
        
        # Recupera default dal JSON salvato
        default_params = saved_config.get("strategies_params", {}).get(selected_strat, {})
        
        st.subheader("Parameters Override")
        st.caption("Modifica i parametri per questo test (non salva nel sistema).")
        
        # UI Dinamica per Override Parametri
        # I valori inseriti qui finiscono nel dizionario 'params'
        if selected_strat == "RSI":
            params['rsi_period'] = st.number_input("RSI Period", value=default_params.get('rsi_period', 14))
            params['rsi_lower'] = st.number_input("Lower (<)", value=default_params.get('rsi_lower', 30))
            params['rsi_upper'] = st.number_input("Upper (>)", value=default_params.get('rsi_upper', 70))
            params['atr_period'] = st.number_input("ATR Period", value=default_params.get('atr_period', 14))
            
        elif selected_strat == "EMA":
            params['short_window'] = st.number_input("Fast EMA", value=default_params.get('short_window', 50))
            params['long_window'] = st.number_input("Slow EMA", value=default_params.get('long_window', 200))
            params['atr_period'] = st.number_input("ATR Period", value=default_params.get('atr_period', 14))
            
    st.markdown("---")
    st.subheader("Simulation Settings")
    initial_cap = st.number_input("Initial Capital (€)", value=10000, step=1000)
    years = st.slider("History (Years)", 1, 5, 2)
    
    run_btn = st.button("🚀 RUN SIMULATION", type="primary")

# --- MAIN AREA ---

tab_run, tab_results = st.tabs(["🚀 Run Simulation", "📊 Results Analysis"])

# TAB 1: ESECUZIONE
with tab_run:
    if run_btn:
        st.info("Simulation started... please wait.")
        progress_bar = st.progress(0)
        
        try:
            session_path = ""
            
            # CHIAMATA DIRETTA AL BACKEND
            if mode == "Benchmark (Run All)":
                # Esegue tutte le strategie usando i parametri nel JSON
                session_path = run_backtest_session(
                    mode="ALL",
                    initial_capital=initial_cap,
                    years=years
                )
            else:
                # Esegue singola strategia usando i parametri della Sidebar (params)
                session_path = run_backtest_session(
                    mode="SINGLE_OVERRIDE",
                    override_strat_name=selected_strat,
                    override_params=params, # <--- Qui passiamo l'override!
                    initial_capital=initial_cap,
                    years=years
                )

            progress_bar.progress(100)
            
            if session_path:
                st.success(f"Simulation completed! Path: {session_path}")
                # Salviamo il path nella sessione per aprirlo automaticamente nel tab Results
                st.session_state['last_run_path'] = session_path
                st.rerun() 
            else:
                st.error("Simulation returned empty path. Check logs.")
                    
        except Exception as e:
            st.error(f"Critical Error during execution: {e}")

# TAB 2: ANALISI RISULTATI
with tab_results:
    st.write("### 📂 Results Browser")
    
    base_dir = Path("data/backtests")
    if not base_dir.exists():
        st.warning("No backtests found yet.")
        st.stop()
        
    # Elenco sessioni (Timestamp) ordinate dalla più recente
    sessions = sorted([x.name for x in base_dir.iterdir() if x.is_dir()], reverse=True)
    
    # Selettore Sessione (Default: l'ultima appena eseguita)
    default_idx = 0
    if 'last_run_path' in st.session_state:
        last_name = Path(st.session_state['last_run_path']).name
        if last_name in sessions:
            default_idx = sessions.index(last_name)

    selected_session = st.selectbox("Select Session (Timestamp)", sessions, index=default_idx)
    
    if selected_session:
        session_path = base_dir / selected_session
        st.caption(f"Viewing Data from: {session_path}")
        
        # CARICAMENTO DATI
        strat_data, summary_df = load_benchmark_data(session_path)
        
        if not strat_data:
            st.warning("This session folder appears to be empty.")
        else:
            # 1. GRAFICO COMPARATIVO PLOTLY
            st.subheader("📈 Equity Curve Comparison")
            fig = plot_comparison(strat_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. TABELLA METRICHE RIASSUNTIVE
            st.subheader("🏆 Performance Summary")
            st.dataframe(
                summary_df.style.format({
                    "Final Equity": "€ {:,.2f}",
                    "ROI %": "{:+.2f}%"
                }).background_gradient(subset=["ROI %"], cmap="RdYlGn"),
                use_container_width=True,
                hide_index=True
            )
            
            st.markdown("---")
            
            # 3. DETTAGLIO SINGOLA STRATEGIA
            st.subheader("🔍 Deep Dive: Strategy Details")
            
            col_sel_strat, col_space = st.columns([1, 2])
            with col_sel_strat:
                strat_keys = list(strat_data.keys())
                detail_strat = st.selectbox("Inspect Strategy:", strat_keys)
            
            if detail_strat:
                d_data = strat_data[detail_strat]
                d_path = d_data['path']
                
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.write("**Configuration Used:**")
                    st.json(d_data['config'].get('params', {}))
                    st.write("**Stats:**")
                    st.write(f"- Initial Capital: € {d_data['config'].get('initial_capital', 0):,.2f}")
                    st.write(f"- Final Equity: € {d_data['config'].get('final_equity', 0):,.2f}")
                
                with c2:
                    st.write("**Trade History (Top 50):**")
                    trades_csv = d_path / "trades.csv"
                    if trades_csv.exists():
                        df_trades = pd.read_csv(trades_csv)
                        if not df_trades.empty:
                            st.dataframe(df_trades.head(50), height=300, use_container_width=True)
                        else:
                            st.info("No trades executed.")
                    else:
                        st.info("Trades file not found.")