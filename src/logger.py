import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os

# Determina path assoluto basato sulla posizione di questo file
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

# Assicuriamoci che la cartella esista (anche se manager.sh dovrebbe averlo fatto)
try:
    LOG_DIR.mkdir(exist_ok=True)
except Exception:
    pass # Se manca i permessi, l'handler file fallirà ma console andrà

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    # Livello di default (sovrascrivibile da .env se implementato)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (Fondamentale per Docker logs)
    # Usiamo sys.stdout e forziamo il flush se necessario
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 2. File Handler (Solo se la cartella è scrivibile)
    try:
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding='utf-8' # Importante per simboli valuta o emoji
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except PermissionError:
        # Se non possiamo scrivere su file, stampiamo un errore su console ma continuiamo
        sys.stderr.write(f"WARNING: No write permission for logs in {LOG_DIR}\n")

    return logger