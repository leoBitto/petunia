import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import subprocess
from src.strategies import STRATEGY_MAP
from src.settings_manager import SettingsManager

st.set_page_config(page_title="Backtest Lab", page_icon="🧪", layout="wide")
st.title("🧪 Backtest Laboratory")

# --- HELPER FUNCTIONS ---
def load_benchmark_data(session_path: Path):
    """
    Scansiona una cartella di sessione (TIMESTAMP) e carica i dati di tutte le strategie trovate.
    Ritorna:
      - strategies_data: dict { 'StrategyName': {'equity': df, 'config': dict} }
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
    
    # Carica parametri salvati per pre-compilare
    try:
        manager = SettingsManager()
        saved_config = manager.load_config()
    except:
        saved_config = {}

    selected_strat = None
    params = {}
    
    if mode == "Single Strategy":
        selected_strat = st.selectbox("Select Strategy", list(STRATEGY_MAP.keys()))
        
        # Parametri override (UI semplificata per RSI/EMA)
        default_params = saved_config.get("strategies_params", {}).get(selected_strat, {})
        st.subheader("Parameters Override")
        
        if selected_strat == "RSI":
            params['rsi_period'] = st.number_input("RSI Period", value=default_params.get('rsi_period', 14))
            params['rsi_lower'] = st.number_input("Lower", value=default_params.get('rsi_lower', 30))
            params['rsi_upper'] = st.number_input("Upper", value=default_params.get('rsi_upper', 70))
            params['atr_period'] = st.number_input("ATR", value=default_params.get('atr_period', 14))
        elif selected_strat == "EMA":
            params['short_window'] = st.number_input("Fast EMA", value=default_params.get('short_window', 50))
            params['long_window'] = st.number_input("Slow EMA", value=default_params.get('long_window', 200))
            params['atr_period'] = st.number_input("ATR", value=default_params.get('atr_period', 14))
            
    st.markdown("---")
    initial_cap = st.number_input("Initial Capital (€)", value=10000, step=1000)
    years = st.slider("History (Years)", 1, 5, 2)
    
    run_btn = st.button("🚀 RUN SIMULATION", type="primary")

# --- MAIN AREA ---
tab_run, tab_results = st.tabs(["🚀 Run Simulation", "📊 Results Analysis"])

with tab_run:
    if run_btn:
        st.info("Simulation started... please wait.")
        progress_bar = st.progress(0)
        
        try:
            # Costruzione comando per subprocess
            # Usiamo subprocess per garantire che il backtest giri in un processo pulito
            # e per supportare facilmente la modalità 'ALL' gestita dal main() del backend.
            cmd = ["python", "-m", "services.backtest"]
            
            if mode == "Benchmark (Run All)":
                cmd.append("ALL")
            else:
                cmd.append(selected_strat)
                # Nota: Per passare i parametri override al subprocess servirebbe un meccanismo CLI più complesso.
                # Per ora, in modalità Single, questo userà i parametri del JSON salvato se non modifichiamo services/backtest.py
                # PER ORA: Accettiamo che il 'Single' da UI legga dal JSON o implementiamo un fix rapido.
                # FIX RAPIDO: Per semplicità, in questa versione 'Single' usa i parametri salvati nel JSON.
                # Se vuoi l'override live, dovremmo passare i parametri come stringa JSON al comando CLI.
            
            # Esecuzione
            process = subprocess.run(cmd, capture_output=True, text=True)
            progress_bar.progress(100)
            
            if process.returncode == 0:
                st.success("Simulation completed successfully!")
                
                # Parsing dell'output per trovare dove ha salvato i dati
                # Cerchiamo la riga "Cartella Sessione: ..." nei log
                for line in process.stdout.splitlines() + process.stderr.splitlines():
                    if "Cartella Sessione:" in line:
                        session_path_str = line.split("Cartella Sessione:")[-1].strip()
                        st.session_state['last_run_path'] = session_path_str
                        st.experimental_rerun() # Ricarica per mostrare i risultati nel tab Results
            else:
                st.error("Error during execution.")
                with st.expander("Show Error Logs"):
                    st.code(process.stderr)
                    st.code(process.stdout)
                    
        except Exception as e:
            st.error(f"Critical Error: {e}")

with tab_results:
    st.write("### 📂 Results Browser")
    
    base_dir = Path("data/backtests")
    if not base_dir.exists():
        st.warning("No backtests found.")
        st.stop()
        
    # Elenco sessioni (Timestamp) ordinate dalla più recente
    sessions = sorted([x.name for x in base_dir.iterdir() if x.is_dir()], reverse=True)
    
    # Se abbiamo appena finito una run, selezionala di default
    default_idx = 0
    if 'last_run_path' in st.session_state:
        last_name = Path(st.session_state['last_run_path']).name
        if last_name in sessions:
            default_idx = sessions.index(last_name)

    selected_session = st.selectbox("Select Session (Timestamp)", sessions, index=default_idx)
    
    if selected_session:
        session_path = base_dir / selected_session
        st.caption(f"Path: {session_path}")
        
        # CARICAMENTO DATI
        strat_data, summary_df = load_benchmark_data(session_path)
        
        if not strat_data:
            st.warning("Empty session folder.")
        else:
            # 1. GRAFICO COMPARATIVO
            st.subheader("📈 Equity Curve Comparison")
            fig = plot_comparison(strat_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # 2. TABELLA METRICHE
            st.subheader("🏆 Performance Summary")
            # Formattazione colonne
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
            st.subheader("🔍 Deep Dive: Single Strategy Details")
            strat_keys = list(strat_data.keys())
            detail_strat = st.selectbox("Inspect Strategy:", strat_keys)
            
            if detail_strat:
                d_data = strat_data[detail_strat]
                d_path = d_data['path']
                
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.write("**Configuration Used:**")
                    st.json(d_data['config'].get('params', {}))
                
                with c2:
                    st.write("**Trade History:**")
                    trades_csv = d_path / "trades.csv"
                    if trades_csv.exists():
                        df_trades = pd.read_csv(trades_csv)
                        st.dataframe(df_trades, height=200, use_container_width=True)
                    else:
                        st.info("No trades executed.")