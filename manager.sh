#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(dirname "$(realpath "$0")")
export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_ROOT/docs/service_account.json"
DATA_DIR="$PROJECT_ROOT/data/db"

log() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

case "${1:-}" in
  start)
    log "🔐 Recupero credenziali dal Google Secret Manager..."
    # Richiama il modulo Python; deve restituire SOLO JSON
    DB_INFO=$(python3 -m services.get_db_secret 2>/dev/null) || {
      log "❌ Errore: impossibile ottenere i secrets dal servizio Python."
      exit 1
    }

    # VALIDAZIONE JSON (usa python per evitare dipendenza jq per il controllo)
    if ! python3 -c "import sys, json; json.load(sys.stdin)" <<<"$DB_INFO" >/dev/null 2>&1; then
      log "❌ Output non è JSON valido. Contenuto restituito:"
      echo "$DB_INFO"
      exit 1
    fi

    # Se il JSON contiene "error" => falliamo
    if echo "$DB_INFO" | jq -e '.error' >/dev/null 2>&1; then
      log "❌ Errore ricevuto dal servizio get_db_secret:"
      echo "$DB_INFO" | jq -r '.error'
      exit 1
    fi

    # Estrai le variabili (usa jq ora che sappiamo che è JSON valido)
    export DB_USER=$(echo "$DB_INFO" | jq -r '.DB_USER')
    export DB_PASSWORD=$(echo "$DB_INFO" | jq -r '.DB_PASSWORD')
    export DB_NAME=$(echo "$DB_INFO" | jq -r '.DB_NAME')
    export DB_HOST=$(echo "$DB_INFO" | jq -r '.DB_HOST')
    export DB_PORT=$(echo "$DB_INFO" | jq -r '.DB_PORT')

    log "📦 Creazione data dir se necessario e avvio dei container..."
    mkdir -p "$DATA_DIR"
    docker compose up -d db

    # Wait for health status (proteggo con timeout)
    log "⏳ Attendo che il DB diventi healthy (timeout 60s)..."
    COUNTER=0
    until [ "$(docker inspect -f '{{.State.Health.Status}}' money_db 2>/dev/null || echo 'none')" == "healthy" ]; do
      sleep 2
      COUNTER=$((COUNTER+2))
      if [ $COUNTER -ge 60 ]; then
        log "❌ Timeout: il container non è diventato 'healthy' dopo $COUNTER secondi."
        docker compose logs --no-color db | sed -n '1,200p'
        exit 1
      fi
      echo -n "."
    done
    echo ""
    log "✅ Database pronto (porta ${DB_PORT})."
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
    log "📊 Stato dei container:"
    docker ps --filter "name=money_db"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
