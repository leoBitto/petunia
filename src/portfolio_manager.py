import pandas as pd
import numpy as np
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
            # Assicuriamoci che i tipi siano corretti per i calcoli e gestiamo i NaN
            self.df_portfolio["size"] = self.df_portfolio["size"].fillna(0).astype(int)
            self.df_portfolio["price"] = self.df_portfolio["price"].fillna(0.0).astype(float)
        
        if not snapshot_dict.get("cash").empty:
            self.df_cash = snapshot_dict["cash"].copy()
            self.df_cash["cash"] = self.df_cash["cash"].astype(float)
            
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
            "cash": self.df_cash,
            "trades": self.df_trades
        }
    def get_positions_counts(self) -> Dict[str, int]:
        """Restituisce un dizionario {ticker: size} per il RiskManager."""
        if self.df_portfolio.empty:
            return {}
        # Crea una Series con indice ticker e valori size, poi converte a dict
        return self.df_portfolio.set_index("ticker")["size"].to_dict()
        
    # ----------------------
    # Business Logic Core
    # ----------------------
    def get_total_equity(self) -> float:
        """
        Calcola il valore totale del portafoglio (Net Liquidation Value).
        Formula: Cash Disponibile + Somma(Size * Current_Price per ogni posizione)
        """
        # 1. Recupero Cash
        cash = 0.0
        if not self.df_cash.empty:
            cash = self.df_cash.iloc[0]["cash"]

        # 2. Recupero Valore Posizioni
        positions_value = 0.0
        if not self.df_portfolio.empty:
            # Calcolo vettoriale: Moltiplica colonna size per colonna price e somma tutto
            # 1. pd.to_numeric forza tutto a numero (o NaN) -> colonna diventa float
            # 2. fillna(0) ora lavora su float -> nessun warning di downcasting da object
            # 3. astype(int) converte il risultato finale
            self.df_portfolio["size"] = pd.to_numeric(
                self.df_portfolio["size"], errors='coerce'
            ).fillna(0).astype(int)

            self.df_portfolio["price"] = pd.to_numeric(
                self.df_portfolio["price"], errors='coerce'
            ).fillna(0.0).astype(float)
            val_series = (self.df_portfolio["size"] * self.df_portfolio["price"])
            positions_value = val_series.sum()

        return float(cash + positions_value)

    def execute_order(self, order: dict):
        """
        Esegue un ordine (BUY/SELL) aggiornando Cash, Posizioni e Storico Trades.
        Usato principalmente dal Backtester o per sincronizzare ordini manuali.
        
        Input order dict:
        {
            "ticker": "AAPL",
            "action": "BUY" | "SELL",
            "quantity": 10,       (o 'size')
            "price": 150.0,
            "stop_loss": 140.0,   (opzionale)
            "take_profit": 160.0, (opzionale, o 'profit_take')
        }
        """
        ticker = order.get("ticker")
        action = order.get("action").upper()
        # Gestiamo sia 'quantity' che 'size' per compatibilità
        qty = int(order.get("quantity", order.get("size", 0)))
        price = float(order.get("price"))
        
        if qty <= 0:
            self.logger.warning(f"Tentativo di esecuzione ordine con qtà <= 0: {order}")
            return

        # Recupero Cash Attuale
        current_cash = 0.0
        currency = "EUR"
        if not self.df_cash.empty:
            current_cash = float(self.df_cash.iloc[0]["cash"])
            currency = self.df_cash.iloc[0]["currency"]

        transaction_value = qty * price
        
        # --- LOGICA BUY ---
        if action == "BUY":
            # 1. Aggiorna Cash
            new_cash = current_cash - transaction_value
            # Nota: Il RiskManager dovrebbe aver già controllato la capienza, ma qui applichiamo cmq
            self.update_cash(new_cash, currency)
            
            # 2. Calcola Nuova Size Posizione
            current_pos_size = 0
            # Se esiste già, prendiamo la size attuale
            mask = self.df_portfolio["ticker"] == ticker
            if not self.df_portfolio.empty and mask.any():
                current_pos_size = int(self.df_portfolio.loc[mask, "size"].iloc[0])
            
            new_size = current_pos_size + qty
            
            # 3. Aggiorna Posizione
            # Nota: aggiorniamo stop loss e profit take solo se forniti nel nuovo ordine
            sl = order.get("stop_loss", order.get("stop_loss")) # Se None, potrebbe restare quello vecchio? 
            # Per semplicità, in questa implementazione sovrascriviamo se presenti nell'ordine
            # Se l'ordine non ha SL (es. market buy manuale), bisognerebbe decidere se tenere il vecchio.
            # Qui assumiamo che l'ordine sia "law".
            
            self.update_position(
                ticker=ticker,
                size=new_size,
                price=price, # Aggiorniamo al prezzo di esecuzione (Mark-to-Market immediato)
                stop_loss=order.get("stop_loss"),
                profit_take=order.get("take_profit", order.get("profit_take"))
            )

        # --- LOGICA SELL ---
        elif action == "SELL":
            # 1. Aggiorna Cash
            new_cash = current_cash + transaction_value
            self.update_cash(new_cash, currency)
            
            # 2. Calcola Nuova Size
            current_pos_size = 0
            mask = self.df_portfolio["ticker"] == ticker
            if not self.df_portfolio.empty and mask.any():
                current_pos_size = int(self.df_portfolio.loc[mask, "size"].iloc[0])
            
            new_size = current_pos_size - qty
            
            # 3. Gestione chiusura o riduzione
            if new_size <= 0:
                # Posizione chiusa: Rimuoviamo la riga dal DataFrame
                if not self.df_portfolio.empty:
                    self.df_portfolio = self.df_portfolio[self.df_portfolio["ticker"] != ticker]
                    self.logger.info(f"[Portfolio] Posizione chiusa su {ticker}.")
            else:
                # Posizione ridotta: Aggiorniamo solo size e prezzo corrente
                # Manteniamo i vecchi SL/TP se non specificati diversamente, 
                # ma solitamente in sell parziale non si cambiano gli stop.
                # Recuperiamo i vecchi valori per non perderli
                old_sl = self.df_portfolio.loc[mask, "stop_loss"].iloc[0]
                old_tp = self.df_portfolio.loc[mask, "profit_take"].iloc[0]
                
                self.update_position(
                    ticker=ticker,
                    size=new_size,
                    price=price,
                    stop_loss=old_sl,
                    profit_take=old_tp
                )

        # 4. Log Trade (Storico)
        self.add_trade(ticker, qty, price, action)


    # ----------------------
    # Helper esistenti
    # ----------------------
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
        """
        alerts = []
        if self.df_portfolio.empty:
            return alerts

        for _, row in self.df_portfolio.iterrows():
            curr = row["price"]
            sl = row["stop_loss"]
            tp = row["profit_take"]
            
            # Check validità (potrebbero essere NaN o None)
            if pd.notna(sl) and curr <= sl:
                alerts.append(f"STOP LOSS HIT: {row['ticker']} @ {curr}")
            elif pd.notna(tp) and curr >= tp:
                alerts.append(f"TARGET HIT: {row['ticker']} @ {curr}")
        
        return alerts

    def add_trade(self, ticker: str, size: int, price: float, action: str):
        """Registra un nuovo trade nel DataFrame trades."""
        trade = {
            "ticker": ticker,
            "size": size,
            "price": price,
            "action": action,
            "date": datetime.now()
        }
        # Creiamo il DF per la singola riga
        new_trade_row = pd.DataFrame([trade])

        if self.df_trades.empty:
            self.df_trades = new_trade_row
        else:
            self.df_trades = pd.concat([self.df_trades, new_trade_row], ignore_index=True)
            
        self.logger.info(f"[Portfolio] Trade eseguito: {action} {size} {ticker} @ {price}")

    def update_position(self, ticker: str, size: int, price: float,
                        stop_loss: float = None, profit_take: float = None):
        """
        Aggiorna o inserisce una posizione nel DataFrame portfolio.
        """
        now = datetime.now()
        mask = self.df_portfolio["ticker"] == ticker if not self.df_portfolio.empty else pd.Series(dtype=bool)
        
        if mask.any():
            # Update esistente
            self.df_portfolio.loc[mask, ["size", "price", "stop_loss", "profit_take", "updated_at"]] = \
                [size, price, stop_loss, profit_take, now]
            self.logger.info(f"[Portfolio] Posizione aggiornata per {ticker}.") # Ridotto log per backtest
        else:
            # Insert nuovo
            new_pos = {
                "ticker": ticker,
                "size": size,
                "price": price,
                "stop_loss": stop_loss,
                "profit_take": profit_take,
                "updated_at": now
            }
            new_pos_row = pd.DataFrame([new_pos])

            if self.df_portfolio.empty:
                self.df_portfolio = new_pos_row
            else:
                self.df_portfolio = pd.concat([self.df_portfolio, new_pos_row], ignore_index=True)
            self.logger.info(f"[Portfolio] Nuova posizione aggiunta: {ticker}.")

    def update_cash(self, cash: float, currency: str = "EUR"):
        """Aggiorna il valore della cassa."""
        now = datetime.now()
        self.df_cash = pd.DataFrame([{
            "cash": cash,
            "currency": currency,
            "updated_at": now
        }])
        self.logger.info(f"[Portfolio] Cassa aggiornata: {cash:.2f} {currency}")

    def get_positions_summary(self) -> pd.DataFrame:
        return self.df_portfolio.copy()

    def get_trades_history(self, limit: int = 10) -> pd.DataFrame:
        if self.df_trades.empty:
            return pd.DataFrame()
        return self.df_trades.sort_values("date", ascending=False).head(limit).reset_index(drop=True)