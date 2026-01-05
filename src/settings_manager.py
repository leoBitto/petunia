import json
import os
from pathlib import Path
from typing import Dict, Any
from src.logger import get_logger

class SettingsManager:
    """
    Gestisce la configurazione dinamica delle strategie (JSON).
    Policy: FAIL FAST. Se il file manca o è corrotto, solleva eccezioni.
    """
    
    def __init__(self, config_path: str = "config/strategies.json"):
        self.logger = get_logger(self.__class__.__name__)
        
        # Risolviamo il path assoluto
        base_path = Path(__file__).parent.parent
        self.file_path = base_path / config_path
        
        # Check esistenza file all'avvio
        if not self.file_path.exists():
            msg = f"CRITICAL: File di configurazione non trovato in {self.file_path}"
            self.logger.critical(msg)
            raise FileNotFoundError(msg)

    def load_config(self) -> Dict[str, Any]:
        """Legge la configurazione dal disco."""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Il file {self.file_path} non è un JSON valido: {e}")
            raise

    def save_config(self, new_config: Dict[str, Any]):
        """Salva la nuova configurazione su disco."""
        try:
            # Creiamo la cartella se non esiste (utile solo al primo deploy se file iniettato)
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w') as f:
                json.dump(new_config, f, indent=4)
            self.logger.info("Configurazione salvata correttamente.")
        except Exception as e:
            self.logger.error(f"Errore salvataggio config: {e}")
            raise

    def get_fees_config(self) -> Dict[str, float]:
        """Ritorna la configurazione commissioni (default: 0)."""
        cfg = self.load_config()
        return cfg.get("fees_config", {"fixed_euro": 0.0, "percentage": 0.0})
        
    def get_active_strategy_name(self) -> str:
        """Ritorna il nome della strategia attiva. Errore se manca."""
        cfg = self.load_config()
        if "active_strategy" not in cfg:
            raise ValueError(f"Chiave 'active_strategy' mancante in {self.file_path}")
        return cfg["active_strategy"]

    def get_risk_params(self) -> Dict[str, Any]:
        """
        Ritorna i parametri di rischio.
        Strict Mode: Alza errore se mancano nel JSON.
        """
        cfg = self.load_config()
        
        if "risk_params" not in cfg:
            raise ValueError(f"CRITICAL: Chiave 'risk_params' mancante in {self.file_path}. Impossibile calcolare il rischio.")
            
        params = cfg["risk_params"]
        
        # Validazione extra opzionale: controlliamo che ci siano le chiavi essenziali
        required = ["risk_per_trade", "stop_atr_multiplier"]
        for key in required:
            if key not in params:
                raise ValueError(f"CRITICAL: Parametro di rischio '{key}' mancante in config.")
                
        return params

    def get_strategy_params(self, strategy_name: str = None) -> Dict[str, Any]:
        """
        Ritorna i parametri per una specifica strategia.
        Se strategy_name è None, usa quella attiva.
        Errore se la strategia non è configurata.
        """
        cfg = self.load_config()
        
        # Determina quale strategia cercare
        target = strategy_name if strategy_name else cfg.get("active_strategy")
        
        if not target:
             raise ValueError("Impossibile determinare la strategia target (active_strategy mancante?)")

        # Cerca i parametri
        all_params = cfg.get("strategies_params", {})
        if target not in all_params:
            raise ValueError(f"Parametri per strategia '{target}' non trovati in 'strategies_params'.")
            
        return all_params[target]