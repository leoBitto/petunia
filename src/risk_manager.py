import pandas as pd
import numpy as np
from typing import List, Dict, Any
from src.logger import get_logger

class RiskManager:
    """
    Risk Manager: Modulo puro.
    Non dipende da PortfolioManager o DatabaseManager.
    Riceve lo stato del portafoglio come argomenti semplici.
    """

    def __init__(self, risk_per_trade: float, stop_atr_multiplier: float):
        """
        Gestisce il dimensionamento delle posizioni e il rischio.
        NON ha valori di default: devono essere passati dal SettingsManager.
        """
        self.logger = get_logger("RiskManager")
        self.risk_per_trade = risk_per_trade         # Es. 0.02 (2%)
        self.stop_atr_multiplier = stop_atr_multiplier

    def evaluate(self, 
                 signals_df: pd.DataFrame, 
                 total_equity: float, 
                 available_cash: float, 
                 current_positions: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Valuta i segnali rispetto ai dati finanziari forniti.
        """
        orders = []
        if signals_df.empty:
            return orders

        # Usiamo variabili locali per simulare l'evoluzione della cassa nel loop
        simulated_cash = available_cash
        
        # LOG INIZIALE: Fondamentale per sapere con quanti soldi stiamo partendo
        self.logger.info(f"Risk Eval Start. Equity: {total_equity:.2f}, Cash: {available_cash:.2f}")

        # -----------------------------------------------------------
        # FASE 1: VENDITE (Generano Cash Virtuale)
        # -----------------------------------------------------------
        sell_signals = signals_df[signals_df['signal'] == 'SELL']
        
        for _, row in sell_signals.iterrows():
            ticker = row['ticker']
            price = row['price']

            if ticker in current_positions:
                size_to_sell = current_positions[ticker]
                if size_to_sell <= 0: 
                    continue

                # LOG VENDITA
                self.logger.info(f"📉 SELLING {ticker}: Qty {size_to_sell} @ {price:.2f}")

                orders.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "order_type": "MARKET",
                    "quantity": size_to_sell,
                    "price": price,
                    "reason": row.get('meta')
                })

                # Aggiorniamo la cassa simulata
                proceeds = size_to_sell * price
                simulated_cash += proceeds
                
                # Rimuoviamo virtualmente
                del current_positions[ticker]

        # -----------------------------------------------------------
        # FASE 2: ACQUISTI (Consumano Cash Virtuale)
        # -----------------------------------------------------------
        buy_signals = signals_df[signals_df['signal'] == 'BUY']

        for _, row in buy_signals.iterrows():
            ticker = row['ticker']
            price = row['price']
            atr = row.get('atr', 0.0)

            # 1. Non comprare se ho già la posizione
            if ticker in current_positions:
                # LOG DEBUG: Skippo perché lo ho già
                self.logger.debug(f"⏭️ SKIP BUY {ticker}: Posizione già in portafoglio.")
                continue
            
            # 2. Validazione ATR
            if atr <= 0 or pd.isna(atr):
                # LOG WARNING: Problema dati
                self.logger.warning(f"⚠️ SKIP BUY {ticker}: ATR non valido ({atr}).")
                continue

            # --- POSITION SIZING ---
            risk_budget = total_equity * self.risk_per_trade 
            stop_distance = atr * self.stop_atr_multiplier
            stop_loss_price = price - stop_distance

            if stop_loss_price <= 0:
                self.logger.warning(f"⚠️ SKIP BUY {ticker}: Stop Price negativo ({stop_loss_price:.2f}).")
                continue

            # Size = Rischio Euro / Rischio per Azione
            shares_calc = risk_budget / stop_distance
            shares = int(np.floor(shares_calc))

            # LOG CRUCIALE: Qui vediamo i calcoli matematici
            # Se shares è 0, vedremo esattamente perché (es. Stop distance troppo grande rispetto al budget)
            self.logger.debug(
                f"🔍 CALC {ticker} | Price: {price:.2f} | ATR: {atr:.2f} | "
                f"RiskBudget: {risk_budget:.2f} | StopDist: {stop_distance:.2f} | "
                f"RawShares: {shares_calc:.4f} -> {shares}"
            )

            # --- CASH CHECK ---
            cost = shares * price
            
            # Se il costo supera la cassa (inclusa quella liberata dalle vendite)
            if cost > simulated_cash:
                max_shares_cash = int(np.floor(simulated_cash / price))
                # LOG CASH: Se ridimensioniamo per mancanza di fondi
                self.logger.debug(f"💰 RESIZE {ticker}: Cash insufficiente ({simulated_cash:.2f} vs Costo {cost:.2f}). Ridotto a {max_shares_cash}.")
                shares = max_shares_cash
                cost = shares * price
            
            if shares < 1:
                # LOG USCITA: Se alla fine la size è 0
                self.logger.debug(f"❌ SKIP {ticker}: Quantità finale pari a 0.")
                continue

            # LOG SUCCESSO
            self.logger.info(f"✅ BUY {ticker}: {shares} shares @ {price:.2f} (Stop: {stop_loss_price:.2f})")

            orders.append({
                "ticker": ticker,
                "action": "BUY",
                "order_type": "LIMIT",
                "quantity": shares,
                "price": price,
                "stop_loss": stop_loss_price,
                "take_profit": price + (stop_distance * 2),
                "atr_at_entry": atr,
                "meta": row.get("meta", {})
            })

            simulated_cash -= cost

        return orders
        
    def check_intraday_stops(self, 
                             current_positions: Dict[str, Any], 
                             daily_prices: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Controlla Stop Loss e Take Profit intraday.
        Gestisce il GAP RISK: se Open < Stop Loss, esce all'Open.
        """
        orders = []
        
        for ticker, pos_data in current_positions.items():
            stop_loss = pos_data.get('stop_loss')
            take_profit = pos_data.get('take_profit')
            qty = pos_data.get('quantity') # Assicurati che la chiave sia 'quantity' o 'size'
            
            # Se non abbiamo dati per questo ticker oggi, saltiamo
            if ticker not in daily_prices:
                continue
            
            # Estraiamo i prezzi di oggi
            today_open = daily_prices[ticker]['open']
            today_low = daily_prices[ticker]['low']
            today_high = daily_prices[ticker]['high']
            
            # 1. LOGICA STOP LOSS (con GAP PROTECTION)
            if stop_loss and today_low <= stop_loss:
                # Se il mercato ha aperto GIÀ sotto lo stop (Gap Down), usciamo all'Open
                # Altrimenti usciamo al prezzo di Stop
                exit_price = stop_loss
                reason = "STOP_LOSS"
                
                if today_open < stop_loss:
                    exit_price = today_open
                    reason = "STOP_LOSS_GAP"
                    self.logger.warning(f"📉 GAP DOWN su {ticker}: Open {today_open} < SL {stop_loss}. Uscita all'Open.")
                else:
                    self.logger.info(f"🛑 STOP LOSS HIT per {ticker}: Low {today_low} <= SL {stop_loss}")

                orders.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "reason": reason,
                    "quantity": qty,
                    "price": exit_price 
                })
                continue # Se scatta lo stop, non controlliamo il target
                
            # 2. LOGICA TAKE PROFIT
            if take_profit and today_high >= take_profit:
                # Anche qui ci potrebbe essere un Gap Up, ma per ora usciamo al TP
                # (conservativo: se apre sopra, prendiamo comunque il TP)
                exit_price = take_profit
                if today_open > take_profit:
                    exit_price = today_open # Bonus: Gap Up a nostro favore!
                
                self.logger.info(f"💰 TAKE PROFIT HIT per {ticker}: High {today_high} >= TP {take_profit}")
                orders.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "reason": "TAKE_PROFIT",
                    "quantity": qty,
                    "price": exit_price
                })
                
        return orders