# 🧠 DEV NOTES — Progetto "Wheres My Money"

Questo documento serve come **diario tecnico** e **guida rapida per sviluppatori**.  
Descrive l’architettura attuale, i comandi utili e le convenzioni di lavoro per mantenere coerenza nel progetto.

---

## 🚀 Obiettivo del progetto

Costruire un sistema **semplice, automatizzato e scalabile** per:

- raccogliere dati giornalieri di mercato (OHLCV)
- gestire portafoglio e storico operazioni
- generare segnali e report settimanali
- eseguire backtest su strategie personalizzate

---

## 🧩 Architettura generale (fase attuale)

```

.
├── config/               # Configurazioni statiche del progetto
├── logs/                 # File di log con rotazione automatica
├── src/                  # Codice di business (classi principali)
│   ├── drive_manager.py
│   ├── logger.py
│   └── ...
├── scripts/              # Script richiamati da systemd o scheduler
│   ├── tester.py
│   ├── daily_run.py
│   └── weekly_run.py
├── services/             # Servizi infrastrutturali (supporto agli script)
│   └── get_db_secret.py  # Recupero credenziali DB dal Secret Manager
├── data/
│   └── db/               # Volume persistente PostgreSQL
├── manager.sh            # Script di gestione ambiente locale e container
├── docker-compose.yml    # Definizione del servizio PostgreSQL (container)
├── docs/                 # Documentazione e credenziali
│   └── service_account.json
└── requirements.txt

````

---

## ⚙️ Setup ambiente locale

### 1️⃣ Creazione ambiente virtuale

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
````

---

### 2️⃣ Credenziali Google Cloud

Il progetto utilizza un **Service Account** per autenticarsi ai servizi Google
(Secret Manager, Drive, Sheets, ecc.).

1. Il file si trova in:

   ```bash
   docs/service_account.json
   ```

2. Esporta la variabile d’ambiente prima di ogni sessione:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/Progetti/wheres_my_money/docs/service_account.json"
   ```

3. Verifica che sia corretta:

   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

---

## 🐘 Database & Docker

### Descrizione

Il database **PostgreSQL** non è installato localmente ma eseguito in container Docker per:

* evitare conflitti o carico inutile sul sistema
* mantenere un ambiente coerente tra dev e produzione
* poter ripristinare facilmente lo stato del DB

### File: `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16
    container_name: money_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - ./data/db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 5s
      timeout: 3s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

```

### Note

* Il volume `./data/db` conserva i dati tra un riavvio e l’altro.
  Se non esiste, viene creato automaticamente da Docker.
* Le credenziali (`DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`)
  vengono caricate automaticamente dal **Google Secret Manager**.

---

## 🔐 Secret Manager

Il recupero delle credenziali è gestito dal modulo:

```
services/get_db_secret.py
```

Questo script:

1. Si autentica usando `GOOGLE_APPLICATION_CREDENTIALS`
2. Recupera i secret dal progetto GCP
3. Esporta le variabili d’ambiente per Docker Compose

### Esecuzione diretta (debug)

```bash
python -m services.get_db_secret
```

Output atteso:

```
[2025-10-18 10:32:10] 🔐 Recupero credenziali dal Google Secret Manager...
DB_USER=postgres
DB_PASSWORD=********
DB_NAME=money
DB_PORT=5432
```

---

## 🧭 Gestione ambiente: `manager.sh`

Lo script `manager.sh` centralizza le operazioni principali di sviluppo:

### Comandi disponibili

```bash
bash manager.sh start     # Avvia il container e imposta le variabili dal Secret Manager
bash manager.sh stop      # Ferma il container
bash manager.sh restart   # Riavvia il container
bash manager.sh logs      # Mostra i log del container
bash manager.sh status    # Mostra lo stato del DB
```

Esempio:

```bash
bash manager.sh start
```

Output atteso:

```
[2025-10-18 11:01:14] 🔐 Recupero credenziali dal Google Secret Manager...
[2025-10-18 11:01:16] 📦 Avvio container PostgreSQL (docker compose up -d)...
[2025-10-18 11:01:18] ✅ Database in esecuzione e pronto all'uso!
```

---

## 🧰 Logging

Ogni modulo utilizza `get_logger(__name__)` per loggare su:

* file in `logs/`
* output standard (console)

I log ruotano automaticamente (max 1MB, 3 backup).

---

## 🧠 Convenzioni di esecuzione

Tutti gli script Python vanno eseguiti come **moduli**, ad esempio:

```bash
python -m scripts.tester
python -m scripts.daily_run
python -m scripts.weekly_run
```

Questo assicura import coerenti e riconoscimento corretto dei package (`src`, `config`, `services`).

---

## 🧩 Prossimi step aggiornati

✅ Completato: DriveManager
✅ Completato: integrazione Secret Manager + container PostgreSQL
✅ Completato: DatabaseManager (connessione, creazione tabelle, batch insert)
✅ Completato: YFinanceManager (fetch giornaliero e storico, normalizzazione dati)

⏩ Prossimo: PortfolioManager
Gestione portafogli e posizioni.

⏩ RiskManager
Calcolo rischi e indicatori sui portafogli.

⏩ Backtester
Simulazioni e test di strategie.

⏩ Reporter + servizi daily e weekly
Generazione report PDF/CSV.

⏩ Servizi schedulati per aggiornamenti giornalieri e settimanali.
servizio aggiornamento giornaliero ohlc
servizio aggiornamento giornaliero portfolio
servizio aggiornamento settimanale dei segnali

---

## 💭 Note di design

* **Chiarezza prima di tutto**: moduli piccoli, responsabilità singola.
* **Isolamento**: `src` non richiama mai direttamente `scripts` o `services`.
* **Sicurezza**: i segreti vivono solo nel Secret Manager.
* **Manutenibilità**: tutta la gestione ambiente è centralizzata in `manager.sh`.
* **Deploy-ready**: la stessa struttura sarà utilizzata su Google Cloud VM.

---

*Ultimo aggiornamento:* `2025-10-18`
*Autore:* Leonardo Bitto


