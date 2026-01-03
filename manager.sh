#!/bin/bash

# Identifica l'utente corrente per i permessi Docker
export UID=$(id -u)
export GID=$(id -g)

# Colori
GREEN='\033[0;32m'
RED='\033[0;31m'
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
        
        # 1. Creiamo le cartelle utente (Log e Credenziali)
        mkdir -p logs config/credentials
        
        # 2. Build
        echo -e "${GREEN}Building Docker Images...${NC}"
        docker compose build
        ;;

	start)
        echo -e "${GREEN}Avvio Infrastruttura (DB + Dashboard)...${NC}"
        # Aggiungiamo 'dashboard' alla lista dei servizi da avviare
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
        echo -e "${GREEN}Running Backtest...${NC}"
        docker compose run --rm app python -m services.backtest
        ;;

	test)
        echo -e "${GREEN}Running Tests (Pytest inside Docker)...${NC}"
        # Esegue pytest sulla cartella tests/ con verbosità attiva (-v)
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
        echo "Usage: $0 {setup|start|stop|status|daily|weekly|backtest|test|shell|dashboard}"
        exit 1
        ;;
esac