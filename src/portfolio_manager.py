import pandas as pd
from datetime import datetime
from src.logger import get_logger


class PortfolioManager:
    """
    Gestisce la logica di portafoglio in memoria (posizioni, cassa, trades).

    ⚙️ Il DatabaseManager gestisce la persistenza, mentre questa classe
    si occupa della parte di business logic:
      - mantenere e aggiornare i DataFrame locali
      - gestire le operazioni di trading e di cassa
      - esportare o importare snapshot completi del portafoglio
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        # Snapshot in memoria
        self.df_portfolio = pd.DataFrame(columns=["ticker", "size", "price", "stop_loss", "profit_take", "updated_at"])
        self.df_cash = pd.DataFrame(columns=["cash", "currency", "updated_at"])
        self.df_trades = pd.DataFrame(columns=["ticker", "size", "price", "action", "date"])

        self.logger.info("PortfolioManager inizializzato con strutture vuote.")

    # ----------------------
    # Load & Save
    # ----------------------
    def load_from_db(self, snapshot_dict: dict):
        """Usa il dizionario restituito esattamente da db.load_portfolio()"""
        self.logger.info("Caricamento stato Portfolio...")
        
        # Gestione robusta: se il DB è vuoto, usa i DF vuoti init
        if not snapshot_dict.get("portfolio").empty:
            self.df_portfolio = snapshot_dict["portfolio"].copy()
            # Assicuriamoci che i tipi siano corretti per i calcoli
            self.df_portfolio["size"] = self.df_portfolio["size"].fillna(0).astype(int)
            self.df_portfolio["price"] = self.df_portfolio["price"].astype(float)
        
        if not snapshot_dict.get("cash").empty:
            self.df_cash = snapshot_dict["cash"].copy()
            
        if not snapshot_dict.get("trades").empty:
            self.df_trades = snapshot_dict["trades"].copy()

        self.logger.info("[Portfolio] Snapshot caricato dal DB.")

    def get_snapshot(self) -> dict:
        """Restituisce uno snapshot completo del portafoglio come dizionario di DataFrame."""
        # Aggiorna timestamp prima di salvare
        now = datetime.now()
        if not self.df_portfolio.empty:
            self.df_portfolio["updated_at"] = now
        
        return {
            "portfolio": self.df_portfolio,
            "cash": self.df_cash, # Nota: il cash va gestito (vedi sotto)
            "trades": self.df_trades
        }

    # ----------------------
    # Gestione operazioni
    # ----------------------

    # --- BUSINESS LOGIC ---
    def update_market_prices(self, current_prices: dict):
        """
        Aggiorna solo la colonna 'price' (Mark-to-Market).
        Input: {'AAPL': 155.0, 'MSFT': 300.0}
        """
        if self.df_portfolio.empty:
            return

        now = datetime.now()
        # Iterazione efficiente su Pandas
        for ticker, new_price in current_prices.items():
            mask = self.df_portfolio["ticker"] == ticker
            if mask.any():
                self.df_portfolio.loc[mask, "price"] = new_price
                self.df_portfolio.loc[mask, "updated_at"] = now

    def check_stops_and_targets(self) -> list:
        """
        Restituisce una lista di allarmi se un prezzo ha superato i livelli.
        NON vende automaticamente (dato che operi manualmente), ma ti avvisa.
        """
        alerts = []
        if self.df_portfolio.empty:
            return alerts

        for _, row in self.df_portfolio.iterrows():
            curr = row["price"]
            sl = row["stop_loss"]
            tp = row["profit_take"]
            
            if sl and curr <= sl:
                alerts.append(f"STOP LOSS HIT: {row['ticker']} @ {curr}")
            elif tp and curr >= tp:
                alerts.append(f"TARGET HIT: {row['ticker']} @ {curr}")
        
        return alerts

    def add_trade(self, ticker: str, size: int, price: float, action: str):
        """
        Registra un nuovo trade nel DataFrame trades.
        Il RiskManager o altri moduli si occuperanno della coerenza logica.
        """
        trade = {
            "ticker": ticker,
            "size": size,
            "price": price,
            "action": action,
            "date": datetime.now()
        }
        self.df_trades = pd.concat([self.df_trades, pd.DataFrame([trade])], ignore_index=True)
        self.logger.info(f"[Portfolio] Nuovo trade registrato: {trade}")

    def update_position(self, ticker: str, size: int, price: float,
                        stop_loss: float = None, profit_take: float = None):
        """
        Aggiorna o inserisce una posizione nel DataFrame portfolio.
        """
        now = datetime.now()
        mask = self.df_portfolio["ticker"] == ticker if not self.df_portfolio.empty else pd.Series(dtype=bool)
        if mask.any():
            self.df_portfolio.loc[mask, ["size", "price", "stop_loss", "profit_take", "updated_at"]] = \
                [size, price, stop_loss, profit_take, now]
            self.logger.info(f"[Portfolio] Posizione aggiornata per {ticker}.")
        else:
            new_pos = {
                "ticker": ticker,
                "size": size,
                "price": price,
                "stop_loss": stop_loss,
                "profit_take": profit_take,
                "updated_at": now
            }
            self.df_portfolio = pd.concat([self.df_portfolio, pd.DataFrame([new_pos])], ignore_index=True)
            self.logger.info(f"[Portfolio] Nuova posizione aggiunta: {ticker}.")

    def update_cash(self, cash: float, currency: str = "EUR"):
        """
        Aggiorna il valore della cassa. Sovrascrive eventuali record precedenti.
        """
        now = datetime.now()
        self.df_cash = pd.DataFrame([{
            "cash": cash,
            "currency": currency,
            "updated_at": now
        }])
        self.logger.info(f"[Portfolio] Cassa aggiornata: {cash} {currency}")

    # ----------------------
    # Utility
    # ----------------------
    def get_positions_summary(self) -> pd.DataFrame:
        """Restituisce una vista riassuntiva delle posizioni correnti."""
        return self.df_portfolio.copy()

    def get_trades_history(self, limit: int = 10) -> pd.DataFrame:
        """Restituisce gli ultimi `n` trade eseguiti."""
        if self.df_trades.empty:
            return pd.DataFrame()
        return self.df_trades.sort_values("date", ascending=False).head(limit).reset_index(drop=True)
