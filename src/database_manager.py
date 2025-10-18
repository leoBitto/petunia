# src/database_manager.py
from datetime import datetime
from typing import List, Optional
import psycopg
from psycopg.rows import dict_row

from services.get_db_secret import get_db_credentials
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
        """Crea la connessione usando i secrets dal Secret Manager"""
        try:
            creds = get_db_credentials()
            self.conn = psycopg.connect(
                host=creds["DB_HOST"],
                port=int(creds["DB_PORT"]),
                dbname=creds["DB_NAME"],
                user=creds["DB_USER"],
                password=creds["DB_PASSWORD"],
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
                updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT now()
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


    # ----------------------
    # Portfolio
    # ----------------------
    def update_portfolio(self, data: dict):
        """Aggiorna o inserisce una posizione nel portafoglio"""
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO portfolio(ticker, stop_loss, profit_take, size, price, updated_at)
            VALUES (%(ticker)s, %(stop_loss)s, %(profit_take)s, %(size)s, %(price)s, %(updated_at)s)
            ON CONFLICT (ticker) DO UPDATE
            SET stop_loss = EXCLUDED.stop_loss,
                profit_take = EXCLUDED.profit_take,
                size = EXCLUDED.size,
                price = EXCLUDED.price,
                updated_at = EXCLUDED.updated_at;
            """, data)
            self.conn.commit()

    def add_trade(self, data: dict):
        """Aggiunge una nuova operazione al portfolio_trades"""
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO portfolio_trades(ticker, size, price, action, date)
            VALUES (%(ticker)s, %(size)s, %(price)s, %(action)s, %(date)s);
            """, data)
            self.conn.commit()
