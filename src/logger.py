# src/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """Ritorna un logger con rotazione file e output su console."""
    logger = logging.getLogger(name)

    # Evita doppie configurazioni
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # === Formatter coerente e leggibile ===
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # === File handler con rotazione ===
    file_handler = RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=2_000_000,  # 2 MB
        backupCount=3
    )
    file_handler.setFormatter(formatter)

    # === Stream handler (stdout, visibile in console e journalctl) ===
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # === Aggiungi entrambi ===
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
