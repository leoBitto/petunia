#!/bin/bash

# Identifica l'utente corrente per i permessi Docker
export UID=$(id -u)
export GID=$(id -g)

# Colori
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m' # Aggiunto giallo per info
NC='\033[0m'

# Verifica esistenza .env
if [ ! -f .env ]; then
    echo -e "${RED}ERRORE: File .env mancante!${NC}"
    echo "Copia .env.example in .env e inserisci i tuoi dati."
    exit 1
fi

case "$1" in
    setup)
        echo -e "${GREEN}Inizializzazione Petunia Environment...${NC}"
        
        # 1. Creiamo le cartelle utente PRIMA di Docker
        # Questo garantisce che l'owner sia l'utente corrente ($UID), non root
        mkdir -p logs 
        mkdir -p config/credentials 
        mkdir -p data/backtests
        
        # 2. Build
        echo -e "${GREEN}Building Docker Images...${NC}"
        docker compose build
        ;;

    start)
        echo -e "${GREEN}Avvio Infrastruttura (DB + Dashboard)...${NC}"
        docker compose up -d db dashboard
        ;;

    init)
        echo -e "${GREEN}Inizializzazione Tabelle DB...${NC}"
        docker compose run --rm app python -m services.init_db
        ;;

    daily)
        echo -e "${GREEN}Running Daily Service...${NC}"
        docker compose run --rm app python -m services.daily_run
        ;;

    weekly)
        echo -e "${GREEN}Running Weekly Service...${NC}"
        docker compose run --rm app python -m services.weekly_run
        ;;
    
    backtest)
        # Catturiamo gli argomenti extra (es: ALL o EMA)
        ARGS="${@:2}"
        if [ -z "$ARGS" ]; then
            INFO="(Default Active Strategy)"
        else
            INFO="(Target: $ARGS)"
        fi
        
        echo -e "${GREEN}Running Backtest $INFO...${NC}"
        # Passiamo gli argomenti extra allo script Python
        docker compose run --rm app python -m services.backtest $ARGS
        ;;

    test)
        echo -e "${GREEN}Running Tests (Pytest inside Docker)...${NC}"
        docker compose run --rm app pytest tests/ -v
        ;;
        
    shell)
        echo -e "${GREEN}Opening Shell...${NC}"
        docker compose run --rm -it app /bin/bash
        ;;

    status)
        docker compose ps
        ;;

    stop)
        echo -e "${GREEN}Stopping Containers...${NC}"
        docker compose down
        ;;

    dashboard)
        echo "Log Dashboard (Streamlit)..."
        docker compose logs -f dashboard
        ;;

    *)
        echo -e "${YELLOW}Usage: $0 {command} [args]${NC}"
        echo "--------------------------------------------------------"
        echo " 🛠️  SETUP:"
        echo "   setup      -> Build images & create folders"
        echo "   init       -> Create DB schema (Warning: resets data)"
        echo ""
        echo " 🚀 RUNTIME:"
        echo "   start      -> Start DB & Dashboard (background)"
        echo "   stop       -> Stop all containers"
        echo "   status     -> Check containers status"
        echo "   dashboard  -> View Dashboard logs"
        echo ""
        echo " 🧠 SERVICES:"
        echo "   daily      -> Run Data Fetch & Portfolio Update"
        echo "   weekly     -> Run Strategy Analysis (Friday)"
        echo "   backtest   -> Run Simulation (Args: ALL, EMA, RSI)"
        echo ""
        echo " 💻 DEV:"
        echo "   test       -> Run Pytest Suite"
        echo "   shell      -> Open Bash inside App container"
        echo "--------------------------------------------------------"
        exit 1
        ;;
esac