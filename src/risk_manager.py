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

    def __init__(self, risk_per_trade: float = 0.02, stop_atr_multiplier: float = 2.0):
        self.logger = get_logger(self.__class__.__name__)
        self.risk_per_trade = risk_per_trade
        self.stop_atr_multiplier = stop_atr_multiplier

    def evaluate(self, 
                 signals_df: pd.DataFrame, 
                 total_equity: float, 
                 available_cash: float, 
                 current_positions: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        Valuta i segnali rispetto ai dati finanziari forniti.
        
        Input:
            - signals_df: DataFrame dalla Strategia
            - total_equity: Valore totale del portafoglio (Cash + Asset)
            - available_cash: Liquidità corrente
            - current_positions: Dict { 'TICKER': size } per sapere cosa possediamo già
        """
        orders = []
        if signals_df.empty:
            return orders

        # Usiamo variabili locali per simulare l'evoluzione della cassa nel loop
        # NOTA: Non modifichiamo nulla fuori da questa funzione.
        simulated_cash = available_cash
        
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
                if size_to_sell <= 0: continue

                orders.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "order_type": "MARKET",
                    "quantity": size_to_sell,
                    "price": price,
                    "reason": row.get('meta')
                })

                # Aggiorniamo la cassa simulata per permettere nuovi acquisti
                proceeds = size_to_sell * price
                simulated_cash += proceeds
                
                # Rimuoviamo virtualmente per i controlli successivi
                del current_positions[ticker]

        # -----------------------------------------------------------
        # FASE 2: ACQUISTI (Consumano Cash Virtuale)
        # -----------------------------------------------------------
        buy_signals = signals_df[signals_df['signal'] == 'BUY']

        for _, row in buy_signals.iterrows():
            ticker = row['ticker']
            price = row['price']
            atr = row.get('atr', 0.0)

            # 1. Non comprare se ho già la posizione (o se non l'ho venduta sopra)
            if ticker in current_positions:
                continue
            
            # 2. Validazione ATR
            if atr <= 0 or pd.isna(atr):
                continue

            # --- POSITION SIZING ---
            risk_budget = total_equity * self.risk_per_trade 
            stop_distance = atr * self.stop_atr_multiplier
            stop_loss_price = price - stop_distance

            if stop_loss_price <= 0: continue

            # Size = Rischio Euro / Rischio per Azione
            shares_calc = risk_budget / stop_distance
            shares = int(np.floor(shares_calc))

            # --- CASH CHECK ---
            cost = shares * price
            
            # Se il costo supera la cassa (inclusa quella liberata dalle vendite)
            if cost > simulated_cash:
                shares = int(np.floor(simulated_cash / price))
                cost = shares * price
            
            if shares < 1:
                continue

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