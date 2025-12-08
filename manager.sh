#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(dirname "$(realpath "$0")")
export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_ROOT/docs/service_account.json"
DATA_DB_DIR="$PROJECT_ROOT/data/db"
DATA_ORDERS_DIR="$PROJECT_ROOT/data/orders"
VENV_DIR="$PROJECT_ROOT/.env"

log() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

# Funzione per attivare il virtual environment
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    else
        log "❌ Virtual environment non trovato. Esegui './manager.sh setup' prima."
        exit 1
    fi
}

case "${1:-}" in
  setup)
    log "🛠️  Inizio procedura di Setup..."

    # 1. Controllo e Installazione jq
    if ! command -v jq &> /dev/null; then
        log "⚠️  jq non trovato. Tento l'installazione (richiede sudo)..."
        if sudo apt-get update && sudo apt-get install -y jq; then
            log "✅ jq installato correttemente."
        else
            log "❌ Impossibile installare jq automaticamente. Installalo manualmente (es. sudo apt install jq)."
            exit 1
        fi
    else
        log "✅ jq è già installato."
    fi

    # 2. Creazione cartelle dati
    log "📂 Creazione struttura directory in ./data ..."
    mkdir -p "$DATA_DB_DIR"
    mkdir -p "$DATA_ORDERS_DIR"

    # 3. Setup Python Venv
    if [ ! -d "$VENV_DIR" ]; then
        log "🐍 Creazione virtual environment in .env..."
        python3 -m venv "$VENV_DIR"
    fi

    # 4. Installazione dipendenze
    log "⬇️  Installazione dipendenze da requirements.txt..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$PROJECT_ROOT/requirements.txt"
    
    log "✅ Setup completato! Ora puoi lanciare './manager.sh start'"
    ;;

  start)
    # Assicuriamoci che le cartelle esistano
    mkdir -p "$DATA_DB_DIR"
    mkdir -p "$DATA_ORDERS_DIR"
    
    # Attiviamo venv per avere accesso alle lib python per get_db_secret
    activate_venv

    log "🔐 Recupero credenziali dal Google Secret Manager..."
    # Richiama il modulo Python; deve restituire SOLO JSON
    # Nota: Usiamo python del venv
    DB_INFO=$(python -m services.get_db_secret 2>/dev/null) || {
      log "❌ Errore: impossibile ottenere i secrets dal servizio Python."
      exit 1
    }

    # VALIDAZIONE JSON
    if ! python -c "import sys, json; json.load(sys.stdin)" <<<"$DB_INFO" >/dev/null 2>&1; then
      log "❌ Output non è JSON valido. Contenuto restituito:"
      echo "$DB_INFO"
      exit 1
    fi

    if echo "$DB_INFO" | jq -e '.error' >/dev/null 2>&1; then
      log "❌ Errore ricevuto dal servizio get_db_secret:"
      echo "$DB_INFO" | jq -r '.error'
      exit 1
    fi

    export DB_USER=$(echo "$DB_INFO" | jq -r '.DB_USER')
    export DB_PASSWORD=$(echo "$DB_INFO" | jq -r '.DB_PASSWORD')
    export DB_NAME=$(echo "$DB_INFO" | jq -r '.DB_NAME')
    export DB_PORT=$(echo "$DB_INFO" | jq -r '.DB_PORT')

    log "📦 Avvio container PostgreSQL..."
    docker compose up -d db

    log "⏳ Attendo che il DB diventi healthy (timeout 60s)..."
    COUNTER=0
    until [ "$(docker inspect -f '{{.State.Health.Status}}' money_db 2>/dev/null || echo 'none')" == "healthy" ]; do
      sleep 2
      COUNTER=$((COUNTER+2))
      if [ $COUNTER -ge 60 ]; then
        log "❌ Timeout waiting for DB."
        docker compose logs --no-color db | sed -n '1,200p'
        exit 1
      fi
      echo -n "."
    done
    echo ""
    log "✅ Database pronto su porta ${DB_PORT}."
    ;;

  stop)
    log "🛑 Arresto container..."
    docker compose down
    ;;
  
  restart)
    "$0" stop
    "$0" start
    ;;
  
  status)
    log "📊 Stato container:"
    docker ps --filter "name=money_db"
    log "📂 File Ordini Pendenti:"
    ls -l "$DATA_ORDERS_DIR" 2>/dev/null || echo "Nessun ordine pendente."
    ;;

  *)
    echo "Usage: $0 {setup|start|stop|restart|status}"
    exit 1
    ;;
esac