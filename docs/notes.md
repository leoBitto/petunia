```markdown
# 🧠 DEV NOTES — Progetto "Wheres My Money"

Questo documento serve come diario tecnico e guida rapida per lavorare sul progetto in modo coerente e riprendere facilmente il flusso di lavoro dopo una pausa.

---

## 🚀 Obiettivo del progetto

Costruire un sistema semplice e scalabile per:
- raccogliere dati giornalieri di mercato (OHLCV)
- gestire un portafoglio e il suo storico
- generare segnali e report settimanali
- eseguire backtest sulle strategie

---

## 🧩 Architettura generale (fase attuale)

```

.
├── config/               # Configurazioni del progetto
├── logs/                 # File di log con rotazione automatica
├── src/                  # Codice principale (classi)
│   ├── drive_manager.py
│   ├── logger.py
│   └── ...
├── scripts/              # Script eseguibili
│   ├── tester.py
│   ├── daily_run.py
│   └── weekly_run.py
├── docs/                 # Documentazione, chiavi, note
│   └── service_account.json
└── requirements.txt

````

Ogni classe in `src/` è autonoma e può essere richiamata dagli script in `scripts/`. 
Le classi non si devono richiamare tra di loro ma devono essere richiamate dai 
file all'interno di `scripts/`

---

## ⚙️ Setup ambiente locale

### 1️⃣ Creazione ambiente virtuale

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
````

### 2️⃣ Credenziali Google Cloud

Il progetto utilizza un **Service Account JSON** per autenticarsi.

1. Il file si trova in:

   ```
   docs/service_account.json
   ```

2. Esporta la variabile d’ambiente **prima di ogni sessione**:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/Progetti/wheres_my_money/docs/service_account.json"
   ```

3. Puoi verificare:

   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

---

## 🧩 Modulo DriveManager

### Scopo

Gestisce:

* accesso a Google Secret Manager
* autenticazione su Google Sheets
* lettura della lista tickers dal foglio "Universe"

### Uso base

```python
from src.drive_manager import DriveManager

dm = DriveManager()
tickers = dm.get_universe_tickers()
print(tickers)
```

### Log di esempio

```
2025-10-12 15:51:51 | INFO | DriveManager | Secret 'service_account' caricato correttamente.
2025-10-12 15:51:51 | INFO | DriveManager | Autenticazione Google Sheets completata.
2025-10-12 15:51:54 | INFO | DriveManager | Lettura Universe completata: 33 tickers trovati.
```

---

## 🧰 Logging

Ogni modulo usa `get_logger(__name__)` per loggare sia su:

* file dedicato in `logs/`
* standard output

Log ruotano automaticamente (max 1MB, 3 backup).

---

## 🧠 Convenzioni di esecuzione

Tutti gli script vanno eseguiti come moduli (per mantenere import coerenti):

```bash
python -m scripts.tester
python -m scripts.daily_run
python -m scripts.weekly_run
```

Questo assicura che Python riconosca correttamente `src` e `config` come package.

---

## 🧩 Prossimi step

1. ✅ Completato: `DriveManager`
2. 🛠️ In corso: `DatabaseManager` (connessione Postgres, creazione tabelle)
3. ⏩ Poi: `YFinanceManager` (aggiornamento dati OHLCV)
4. 📊 Dopo: `PortfolioManager`, `RiskManager`, `Backtester`
5. 🧾 Infine: `Reporter` + servizi `daily` e `weekly`

---

## 💭 Note di design

* **Semplicità prima di tutto**: nessuna astrazione inutile.
* Tutti i moduli hanno una sola responsabilità chiara.
* I segreti vivono su Google Secret Manager, non in file locali.
* Le configurazioni non sensibili vivono in `config/config.py`.
* Tutto è pensato per essere schedulabile via `systemd`.

---

*Ultimo aggiornamento:* `2025-10-12`
*Autore:* Leonardo Bitto

````

