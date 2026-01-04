import pytest
import json
from src.settings_manager import SettingsManager

# --- FIXTURES ---

@pytest.fixture
def valid_config_data():
    """Dati validi per i test."""
    return {
        "active_strategy": "EMA",
        "strategies_params": {
            "EMA": {"short": 10, "long": 20},
            "RSI": {"period": 14}
        }
    }

@pytest.fixture
def temp_config_file(tmp_path, valid_config_data):
    """
    Crea un file JSON reale in una directory temporanea isolata.
    Ritorna il percorso completo (Path object).
    """
    d = tmp_path / "config"
    d.mkdir()
    f = d / "strategies.json"
    
    # Scriviamo dati validi iniziali
    with open(f, "w") as file:
        json.dump(valid_config_data, file)
        
    return f

# --- TESTS ---

def test_init_fail_if_missing(tmp_path):
    """Deve crashare se il file non esiste (nessun default automatico)."""
    fake_path = tmp_path / "non_existent.json"
    
    # Verifichiamo che alzi l'eccezione giusta
    with pytest.raises(FileNotFoundError):
        SettingsManager(config_path=str(fake_path))

def test_load_success(temp_config_file):
    """Deve caricare correttamente un file valido."""
    # Passiamo il path temporaneo al manager
    manager = SettingsManager(config_path=str(temp_config_file))
    
    # Test active strategy
    assert manager.get_active_strategy_name() == "EMA"
    
    # Test params
    params = manager.get_strategy_params()
    assert params["short"] == 10
    assert params["long"] == 20

def test_missing_active_strategy_key(temp_config_file):
    """Deve alzare ValueError se manca la chiave 'active_strategy'."""
    # Sovrascriviamo il file con dati incompleti
    bad_data = {"strategies_params": {}}
    with open(temp_config_file, "w") as f:
        json.dump(bad_data, f)
        
    manager = SettingsManager(config_path=str(temp_config_file))
    
    with pytest.raises(ValueError, match="active_strategy"):
        manager.get_active_strategy_name()

def test_missing_strategy_params(temp_config_file):
    """Deve alzare ValueError se la strategia attiva non ha parametri definiti."""
    # Configuriamo EMA come attiva, ma non mettiamo i parametri per EMA
    bad_data = {
        "active_strategy": "EMA",
        "strategies_params": {
            "RSI": {"period": 14} 
            # Manca EMA!
        }
    }
    with open(temp_config_file, "w") as f:
        json.dump(bad_data, f)
        
    manager = SettingsManager(config_path=str(temp_config_file))
    
    with pytest.raises(ValueError, match="non trovati"):
        manager.get_strategy_params()

def test_save_config(temp_config_file):
    """Deve salvare correttamente le modifiche su disco."""
    manager = SettingsManager(config_path=str(temp_config_file))
    
    # 1. Modifichiamo la configurazione
    new_config = {
        "active_strategy": "RSI",
        "strategies_params": {
            "RSI": {"period": 99}
        }
    }
    
    # 2. Salviamo
    manager.save_config(new_config)
    
    # 3. Rileggiamo direttamente dal file (bypassando il manager per sicurezza)
    with open(temp_config_file, "r") as f:
        content = json.load(f)
        
    assert content["active_strategy"] == "RSI"
    assert content["strategies_params"]["RSI"]["period"] == 99