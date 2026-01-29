# 🎮 Aroma Bot

Telegram bot avanzato per la gestione di punti, giochi e un sistema RPG completo con combattimento PvE, personaggi, abilità e molto altro.

## ✨ Caratteristiche Principali

### Sistema di Combattimento Avanzato
- **Targeting Modulare**: Sistema di targeting intelligente con `TargetingService` dedicato
- **Fatigue System**: Meccanica di affaticamento realistica al 5% HP
- **Azioni Multiple**: Attacco, difesa (cura 2-3% HP), abilità speciali, fuga
- **Combat AI**: Intelligenza artificiale avanzata per i nemici

### Infrastruttura Robusta
- **CI/CD Pipeline**: Deployment automatizzato con test e rollback automatico
- **Docker Integration**: Containerizzazione completa con PostgreSQL
- **Blue-Green Deployment**: Zero-downtime deployments in produzione
- **Monitoring**: Health checks automatici e logging avanzato

## 🚀 Quick Start

### Sviluppo Locale
```bash
# Clona il repository
git clone <repository-url>
cd aroma

# Installa dipendenze
pip install -r requirements.txt

# Configura variabili d'ambiente
cp .env.example .env
# Modifica .env con i tuoi valori

# Avvia il bot
python3 main.py
```

### Produzione con Docker (Consigliato)
```bash
# Build e avvia i container
docker-compose up -d

# Inizializza database (prima volta)
./init_docker_db.sh

# Verifica stato
./docker_health_check.sh
```

## 📋 Funzionalità Principali

### Sistema RPG
- **Combattimento PvE**: Affronta mob giornalieri e raid boss
- **260+ Personaggi**: Sblocca e equipaggia personaggi da Dragon Ball, Naruto, One Piece e altri
- **Statistiche Avanzate**: Salute, mana, danno, velocità, resistenza, critico
- **Abilità Speciali**: Ogni personaggio ha abilità uniche e trasformazioni
- **Sistema di Fatigue**: Gestione realistica dell'affaticamento in combattimento
- **Azioni di Combattimento**: Attacco, difesa, abilità speciali, fuga

### Sistema di Progressione
- **Livellamento**: Sistema XP con curve di progressione bilanciate
- **Stat Points**: Distribuisci punti nelle statistiche che preferisci
- **Trasformazioni**: Sblocca forme potenziate per i tuoi personaggi
- **Titoli**: Guadagna titoli speciali completando achievement

### Economia e Oggetti
- **Wumpa Coins**: Valuta di gioco guadagnabile
- **Sistema di Drop**: Oggetti, pozioni e collezionabili dai mob
- **Sfere del Drago**: Raccogli 7 sfere per esprimere desideri potenti
- **Equipment**: Equipaggiamento che potenzia le tue statistiche

### Gilde e Sociale
- **Sistema di Gilde**: Crea o unisciti a una gilda
- **Raid Boss**: Affronta boss potenti insieme alla tua gilda
- **Dungeon Cooperativi**: Esplora dungeon con altri giocatori
- **Classifiche**: Compete per il primo posto nelle classifiche globali

## 🛠️ Architettura Tecnica

### Stack Tecnologico
- **Backend**: Python 3.10+ con python-telegram-bot
- **Database**: PostgreSQL 15 (produzione), SQLite (sviluppo)
- **Containerizzazione**: Docker + Docker Compose
- **CI/CD**: GitHub Actions + script automatizzati
- **Deployment**: Blue-green deployment con rollback automatico

### Struttura del Progetto
```
aroma/
├── main.py                 # Entry point del bot
├── database.py             # Configurazione database
├── models/                 # Modelli SQLAlchemy
│   ├── user.py            # Modello utente
│   ├── pve.py             # Modelli combattimento
│   ├── dungeon.py         # Modelli dungeon
│   └── ...
├── services/              # Logica di business
│   ├── pve_service.py     # Servizio combattimento
│   ├── targeting_service.py  # Servizio targeting (NEW)
│   ├── user_service.py    # Servizio utenti
│   ├── dungeon_service.py # Servizio dungeon
│   └── ...
├── data/                  # Dati statici (CSV)
├── images/                # Immagini personaggi/mob
├── tests/                 # Test suite
└── docs/                  # Documentazione
```

### Servizi Modulari
- **TargetingService**: Gestione centralizzata del targeting in combattimento
- **PvEService**: Logica di combattimento PvE
- **DungeonService**: Gestione dungeon e progressione
- **UserService**: Gestione utenti e statistiche
- **ItemService**: Sistema di inventario e oggetti
- **GuildService**: Gestione gilde e raid

## 🐳 Deployment

### Deployment Locale (Test)
```bash
# Avvia in modalità sviluppo
python3 main.py
```

### Deployment Docker (Produzione)
```bash
# Test CI prima del deploy
./ci_test.sh

# Deploy su DietPi con Docker
./docker_deploy.sh

# Rollback se necessario
./docker_rollback.sh
```

### Deployment Tradizionale (Legacy)
```bash
# Deploy senza Docker
./deploy_dietpi.sh

# Rollback
./rollback_dietpi.sh
```

## 📚 Documentazione

- [CI/CD Guide](CI_CD_GUIDE.md) - Guida completa CI/CD
- [Docker Guide](DOCKER_GUIDE.md) - Deployment con Docker
- [Docker Best Practices](docker_best_practices.md) - Best practices Docker
- [Database Init](DOCKER_DB_INIT.md) - Inizializzazione database Docker
- [Project Structure](PROJECT_STRUCTURE.md) - Struttura del progetto
- [Migration Guide](MIGRATION_GUIDE.md) - Guida migrazione database

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pve.py

# Run with coverage
pytest --cov=services --cov-report=html

# CI test suite
./ci_test.sh
```

## 🔧 Configurazione

### Variabili d'Ambiente (.env)
```bash
# Telegram
TELEGRAM_TOKEN=your_bot_token_here

# Database
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aroma_bot
DB_USER=your_user
DB_PASSWORD=your_password

# Environment
TEST=0
TZ=Europe/Rome
```

### Docker Compose
Il progetto include configurazione Docker Compose completa con:
- PostgreSQL 15 con health checks
- Resource limits (CPU/Memory)
- Automatic log rotation
- Network isolation
- Persistent volumes

## 🔐 Sicurezza

- ✅ Utente non-root nei container Docker
- ✅ Secrets management con variabili d'ambiente
- ✅ Network isolation tra container
- ✅ Backup automatici del database
- ✅ Health checks automatici

## 📊 Monitoring

```bash
# Visualizza logs in tempo reale
docker-compose logs -f aroma_bot

# Controlla stato container
docker-compose ps

# Verifica risorse
docker stats

# Health check completo
./docker_health_check.sh
```

## 🤝 Contribuire

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit le tue modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

### Coding Standards
- Usa `black` per formattazione
- Scrivi test per nuove funzionalità
- Documenta le API pubbliche
- Segui i principi SOLID

##  Troubleshooting

### Il bot non si connette al database
```bash
# Verifica configurazione
docker-compose exec aroma_bot env | grep DB

# Controlla logs
docker-compose logs postgres
```

### Errori "relation does not exist"
```bash
# Inizializza database
./init_docker_db.sh
```

### Container non si avvia
```bash
# Rebuild senza cache
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Supporto

Per problemi, domande o suggerimenti:
- Apri una Issue su GitHub
- Contatta gli amministratori del bot
- Consulta la documentazione in `/docs`

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per dettagli.

---

**Made with ❤️ by the Aroma Team**
