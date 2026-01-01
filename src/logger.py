import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os

# Determina path assoluto
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

# Tenta di creare la cartella se non esiste
try:
    LOG_DIR.mkdir(exist_ok=True)
except Exception:
    pass

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Console Handler (Standard Output)
    # StreamHandler di default è unbuffered su stderr, ma usiamo stdout per Docker
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # 2. File Handler (Scrittura su Disco)
    try:
        file_handler = RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding='utf-8',
            delay=False  # Apre subito il file
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        sys.stderr.write(f"WARNING: Impossibile scrivere log su file: {e}\n")

    # --- FORZATURA FLUSH ---
    # Questo è il trucco: aggiungiamo un handler che forza il flush
    # di tutti gli handler dopo ogni record.
    # Costa un po' di performance ma garantisce la scrittura.
    class FlushFilter(logging.Filter):
        def filter(self, record):
            for handler in logger.handlers:
                handler.flush()
            return True
            
    logger.addFilter(FlushFilter())

    return logger