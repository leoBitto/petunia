# src/database_manager.py
from datetime import datetime
from typing import List, Optional
# src/database_manager.py
from datetime import datetime
from typing import List, Optional
import psycopg
from psycopg.rows import dict_row
import pandas as pd
# RIMOSSO: from services.get_db_secret import get_db_credentials
from config import config  # <--- USIAMO QUESTO
from src.logger import get_logger

class DatabaseManager:
    """
    Gestisce la connessione al DB PostgreSQL e tutte le operazioni CRUD principali
    su tabelle: ohlc, portfolio, portfolio_cash, portfolio_trades
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.conn = None
        self._connect()

    def _connect(self):
        """Crea la connessione usando le variabili d'ambiente (via config)."""
        try:
            # ORA LEGGIAMO DA CONFIG, NON DA FUNZIONI ESTERNE
            self.conn = psycopg.connect(
                host=config.DB_HOST,
                port=int(config.DB_PORT),
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                row_factory=dict_row
            )
            self.logger.info("Connessione al DB PostgreSQL stabilita.")
        except Exception as e:
            self.logger.error(f"Errore durante la connessione al DB: {e}")
            raise

    def close(self):
        """Chiude la connessione"""
        if self.conn:
            self.conn.close()
            self.logger.info("Connessione al DB chiusa.")

    def query(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            try:
                return cur.fetchall()
            except Exception:
                return []

    # ----------------------
    # Schema management
    # ----------------------
    def init_schema(self):
        """Crea le tabelle e gli indici se non esistono"""
        self.logger.info("Creazione schema DB...")
        with self.conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS ohlc (
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                volume BIGINT,
                PRIMARY KEY (ticker, date)
            );
            
            CREATE TABLE IF NOT EXISTS portfolio (
                ticker TEXT PRIMARY KEY,
                stop_loss NUMERIC,
                profit_take NUMERIC,
                size INT,
                price NUMERIC,
                updated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS portfolio_cash (
                cash NUMERIC,
                currency TEXT,
                updated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS portfolio_trades (
                id SERIAL PRIMARY KEY,
                ticker TEXT,
                size INT,
                price NUMERIC,
                action TEXT,
                date TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_trades_ticker_date
            ON portfolio_trades(ticker, date);
            """)
            self.conn.commit()
        self.logger.info("Schema DB creato correttamente.")

    def drop_schema(self):
        """Elimina tutte le tabelle (attenzione)"""
        self.logger.warning("Eliminazione schema DB...")
        with self.conn.cursor() as cur:
            cur.execute("""
            DROP TABLE IF EXISTS portfolio_trades;
            DROP TABLE IF EXISTS portfolio_cash;
            DROP TABLE IF EXISTS portfolio;
            DROP TABLE IF EXISTS ohlc;
            """)
            self.conn.commit()
        self.logger.info("Schema DB eliminato.")

    # ----------------------
    # OHLC
    # ----------------------
    def upsert_ohlc(self, data: list[tuple]):
        """
        Inserisce o aggiorna più righe OHLC in batch usando psycopg 3.
        
        Parametri:
        - data: lista di tuple (ticker, date, open, high, low, close, volume)
        
        Requisiti:
        - Ogni tupla deve rispettare l'ordine esatto delle colonne nella query.
        - L'ordine delle tuple nella lista non importa.
        """
        if not data:
            self.logger.info("Nessun dato da inserire.")
            return

        sql = """
        INSERT INTO ohlc(ticker, date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, date) DO UPDATE
        SET open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume;
        """

        try:
            with self.conn.cursor() as cur:
                cur.executemany(sql, data)
                self.conn.commit()
            self.logger.info(f"[DB] Inseriti/aggiornati {len(data)} record OHLC.")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"[DB] Errore durante upsert batch OHLC: {e}")
            raise

    def get_ohlc(self, tickers: list[str], start_date: str, end_date: str) -> List[dict]:
        """Restituisce OHLC tra due date per uno o più ticker"""
        if not tickers:
            return []

        placeholders = ','.join(['%s'] * len(tickers))
        query = f"""
            SELECT * FROM ohlc
            WHERE ticker IN ({placeholders}) AND date BETWEEN %s AND %s
            ORDER BY ticker, date ASC;
        """
        with self.conn.cursor() as cur:
            cur.execute(query, tickers + [start_date, end_date])
            return cur.fetchall()

    def get_ohlc_all_tickers(self, days: int = 365) -> dict:
        """
        Recupera lo storico degli ultimi N giorni per TUTTI i ticker nel DB.
        Restituisce un dizionario ottimizzato per le strategie:
        
        Output:
            {
                "AAPL": pd.DataFrame(...),
                "TSLA": pd.DataFrame(...),
                ...
            }
        """
        # Calcolo data limite
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        # Query unica (molto più veloce di fare un loop per ogni ticker)
        query = """
            SELECT ticker, date, open, high, low, close, volume 
            FROM ohlc 
            WHERE date >= %s
            ORDER BY ticker, date ASC;
        """
        
        with self.conn.cursor() as cur:
            cur.execute(query, (cutoff_date,))
            rows = cur.fetchall()

        if not rows:
            self.logger.warning(f"Nessun dato OHLC trovato negli ultimi {days} giorni.")
            return {}

        # Creiamo un UNICO DataFrame gigante
        df_all = pd.DataFrame(rows)
        
        # Assicuriamoci che i tipi siano corretti
        cols_float = ['open', 'high', 'low', 'close']
        df_all[cols_float] = df_all[cols_float].astype(float)
        df_all['date'] = pd.to_datetime(df_all['date'])
        
        # TRUCCO PANDAS: Groupby per splittare in dizionario
        # Questo crea: {'AAPL': df_aapl, 'TSLA': df_tsla, ...}
        # È molto performante.
        data_map = {ticker: df for ticker, df in df_all.groupby('ticker')}
        
        self.logger.info(f"Caricati dati storici per {len(data_map)} ticker.")
        return data_map


    # ----------------------
    # Portfolio
    # ----------------------
    # ----------------------
    # Portfolio Snapshot
    # ----------------------
    def _load_portfolio_snapshot(self) -> pd.DataFrame:
        """Carica l'intero portafoglio come DataFrame."""
        query = "SELECT * FROM portfolio ORDER BY ticker ASC;"
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def _save_portfolio_snapshot(self, df: pd.DataFrame):
        """
        Aggiorna la tabella portfolio usando UPSERT (più sicuro del TRUNCATE).
        Gestisce anche la cancellazione di posizioni chiuse (size=0).
        """
        if df.empty:
            self.logger.warning("[DB] DataFrame portfolio vuoto.")
            return

        self.logger.info("[DB] Upsert snapshot portfolio...")
        
        # Converto timestamp in stringa se necessario, o mi assicuro che sia datetime
        records = df.to_dict(orient="records")

        sql = """
            INSERT INTO portfolio(ticker, stop_loss, profit_take, size, price, updated_at)
            VALUES (%(ticker)s, %(stop_loss)s, %(profit_take)s, %(size)s, %(price)s, %(updated_at)s)
            ON CONFLICT (ticker) DO UPDATE 
            SET stop_loss = EXCLUDED.stop_loss,
                profit_take = EXCLUDED.profit_take,
                size = EXCLUDED.size,
                price = EXCLUDED.price,
                updated_at = EXCLUDED.updated_at;
        """

        try:
            with self.conn.cursor() as cur:
                cur.executemany(sql, records)
                # Opzionale: Pulizia posizioni chiuse (size = 0)
                cur.execute("DELETE FROM portfolio WHERE size = 0;")
                self.conn.commit()
            self.logger.info(f"[DB] Upsert completato per {len(df)} record.")
        except Exception as e:
            self.logger.error(f"[DB] Errore upsert portfolio: {e}")
            self.conn.rollback()
            raise


    # ----------------------
    # Portfolio Cash
    # ----------------------
    def _load_portfolio_cash(self) -> pd.DataFrame:
        """Carica la situazione di cassa del portafoglio."""
        query = "SELECT * FROM portfolio_cash ORDER BY updated_at DESC;"
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def _save_portfolio_cash(self, df: pd.DataFrame):
        """
        Sovrascrive completamente la tabella 'portfolio_cash' con il contenuto del DataFrame.
        """
        if df.empty:
            self.logger.warning("[DB] DataFrame vuoto: portfolio_cash non aggiornato.")
            return

        self.logger.info("[DB] Salvataggio snapshot portfolio_cash (truncate + insert)...")
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE portfolio_cash;")
            records = df.to_dict(orient="records")
            cur.executemany("""
                INSERT INTO portfolio_cash(cash, currency, updated_at)
                VALUES (%(cash)s, %(currency)s, %(updated_at)s);
            """, records)
            self.conn.commit()
        self.logger.info(f"[DB] Salvati {len(df)} record in 'portfolio_cash'.")


    # ----------------------
    # Portfolio Trades
    # ----------------------
    def _load_portfolio_trades(self) -> pd.DataFrame:
        """Carica la cronologia delle operazioni di trading."""
        query = "SELECT * FROM portfolio_trades ORDER BY date ASC;"
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

    def _save_portfolio_trades(self, df: pd.DataFrame):
        """
        Inserisce nuovi record nella tabella 'portfolio_trades' (append only).
        """
        if df.empty:
            self.logger.warning("[DB] DataFrame vuoto: nessuna operazione salvata.")
            return

        self.logger.info("[DB] Inserimento operazioni in 'portfolio_trades'...")
        with self.conn.cursor() as cur:
            records = df.to_dict(orient="records")
            cur.executemany("""
                INSERT INTO portfolio_trades(ticker, size, price, action, date)
                VALUES (%(ticker)s, %(size)s, %(price)s, %(action)s, %(date)s);
            """, records)
            self.conn.commit()
        self.logger.info(f"[DB] Salvate {len(df)} operazioni in 'portfolio_trades'.")

    # -----------------------
    # Wrapper Portfolio
    # -----------------------
    def load_portfolio(self) -> dict:
        """
        Restituisce un dizionario completo con portfolio, cash e trades.

        Output:
            {
                "portfolio": DataFrame,
                "cash": DataFrame,
                "trades": DataFrame
            }
        """
        self.logger.info("[DB] Caricamento completo del portafoglio...")
        return {
            "portfolio": self._load_portfolio_snapshot(),
            "cash": self._load_portfolio_cash(),
            "trades": self._load_portfolio_trades()
        }

    def save_portfolio(self, snapshot_dict: dict):
        """
        Salva nel database tutti i DataFrame del portafoglio.

        Input:
            {
                "portfolio": DataFrame,
                "cash": DataFrame,
                "trades": DataFrame
            }
        """
        self.logger.info("[DB] Salvataggio completo del portafoglio...")
        self._save_portfolio_snapshot(snapshot_dict.get("portfolio", None))
        self._save_portfolio_cash(snapshot_dict.get("cash", None))
        self._save_portfolio_trades(snapshot_dict.get("trades", None))