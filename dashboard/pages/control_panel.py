import streamlit as st
from pathlib import Path
import time

# Import Servizi Backend
from src.yfinance_manager import YFinanceManager
from src.database_manager import DatabaseManager
from src.drive_manager import DriveManager

st.set_page_config(page_title="Control Panel", page_icon="🕹️", layout="wide")
st.title("🕹️ Control Panel & Maintenance")

# Layout a due colonne principali
col_ops, col_logs = st.columns([1, 1.5])

# --- COLONNA SINISTRA: OPERAZIONI ---
with col_ops:
    st.subheader("🛠️ Data Management")
    
    with st.container(border=True):
        st.write("### 📥 Fetch Historical Data")
        st.caption("Scarica dati da Yahoo Finance e popola il DB.")
        
        # Form per i parametri
        years_to_fetch = st.number_input("Years of History", min_value=1, max_value=10, value=1)
        
        if st.button("🚀 Start Data Fetch", type="primary"):
            status_container = st.status("Avvio procedura di download...", expanded=True)
            try:
                # 1. Recupero Ticker da GSheets
                status_container.write("Lettura Universe da Google Sheets...")
                drive = DriveManager()
                tickers = drive.get_universe_tickers()
                
                if not tickers:
                    status_container.error("Nessun ticker trovato nel foglio 'Universe'!")
                else:
                    status_container.write(f"Trovati {len(tickers)} ticker: {tickers}")
                    
                    # 2. Download da YFinance
                    status_container.write(f"Download di {years_to_fetch} anni di storico...")
                    yf = YFinanceManager()
                    data = yf.fetch_history(tickers, years=years_to_fetch)
                    
                    if data:
                        # 3. Salvataggio DB
                        status_container.write(f"Salvataggio di {len(data)} righe nel Database...")
                        db = DatabaseManager()
                        db.upsert_ohlc(data)
                        
                        status_container.update(label="✅ Operazione completata con successo!", state="complete", expanded=False)
                        st.success(f"Database aggiornato con {len(data)} nuovi record!")
                        time.sleep(2)
                        st.rerun() # Ricarica per aggiornare eventuali metriche
                    else:
                        status_container.error("Nessun dato ricevuto da Yahoo Finance.")
                        
            except Exception as e:
                status_container.error(f"Errore critico: {e}")

    st.markdown("---")
    
    with st.container(border=True):
        st.write("### ⚠️ Danger Zone")
        if st.button("🗑️ Reset Database Schema"):
            if st.checkbox("Confermo di voler cancellare TUTTI i dati"):
                db = DatabaseManager()
                db.drop_schema()
                db.init_schema()
                st.warning("Database resettato e tabelle ricreate.")

# --- COLONNA DESTRA: LOGS ---
with col_logs:
    st.subheader("📜 System Logs Inspector")
    
    # 1. Trova tutti i file .log nella cartella logs/
    log_dir = Path("logs")
    if log_dir.exists():
        # Glob restituisce i file, ne prendiamo solo il nome
        log_files = [f.name for f in log_dir.glob("*.log")]
        
        if log_files:
            # Selectbox per scegliere IL servizio
            selected_file = st.selectbox("Select Log File:", log_files, index=0)
            
            # Slider per quante righe leggere
            lines_count = st.slider("Lines to view:", 10, 200, 50)
            
            # Tasto refresh manuale
            if st.button("🔄 Refresh Logs"):
                st.rerun()
            
            # Lettura e Visualizzazione
            log_path = log_dir / selected_file
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    # Leggiamo tutto e prendiamo le ultime N righe
                    all_lines = f.readlines()
                    tail_lines = all_lines[-lines_count:]
                    
                # Mostriamo in un blocco di codice scrollabile
                log_content = "".join(tail_lines)
                if not log_content.strip():
                    st.info("File di log vuoto.")
                else:
                    st.code(log_content, language="log")
                    
            except Exception as e:
                st.error(f"Impossibile leggere il file: {e}")
        else:
            st.warning("Nessun file .log trovato. Esegui qualche operazione prima!")
    else:
        st.error("Cartella 'logs' non trovata. Verifica il volume Docker.")