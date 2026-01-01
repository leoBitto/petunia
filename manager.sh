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
        
        # 1. Creiamo le cartelle 'umane' (Log e Report) sempre
        mkdir -p logs config/credentials
        
        # 2. Gestione intelligente del DB
        if [ ! -d "data/db" ]; then
            echo "Creazione cartella DB..."
            mkdir -p data/db
        else
            echo "Cartella DB già esistente (Skipping mkdir per evitare errori permessi)."
        fi
        
        # 3. Build dei container
        echo -e "${GREEN}Building Docker Images...${NC}"
        docker compose build
        ;;

    start)
        echo -e "${GREEN}Avvio Database...${NC}"
        docker compose up -d db
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

    *)
        echo "Usage: $0 {setup|start|stop|status|daily|weekly|backtest|shell}"
        exit 1
        ;;
esac