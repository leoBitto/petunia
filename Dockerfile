# Usa un'immagine Python leggera e sicura
FROM python:3.12-slim

# Variabili d'ambiente per Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Imposta la directory di lavoro nel container
WORKDIR /app

# 1. Installiamo prima i requisiti (Sfrutta la cache di Docker!)
# Se cambi il codice ma non i requirements, Docker salta questo step lento.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copiamo tutto il resto del codice
COPY . .

# Comando di default: Mantiene il container acceso ma inattivo.
# Useremo "docker compose run" per lanciare i comandi specifici (daily/weekly).
CMD ["tail", "-f", "/dev/null"]