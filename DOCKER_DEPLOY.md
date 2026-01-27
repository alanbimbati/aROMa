# Docker Deployment Guide

## Opzione 1: Locale con PostgreSQL esistente

Usa il `docker-compose.yml` originale:
```bash
docker-compose up -d
```

Assicurati che `.env` contenga:
```
DB_TYPE=postgresql
DB_HOST=localhost  # o l'IP del tuo server PostgreSQL
DB_PORT=5432
DB_NAME=aroma_bot
DB_USER=aroma_user
DB_PASSWORD=your_password
```

## Opzione 2: Docker con PostgreSQL integrato

Usa `docker-compose-postgresql.yml`:
```bash
docker-compose -f docker-compose-postgresql.yml up -d
```

Questo avvierà:
- Container PostgreSQL (porta 5432)
- Container Aroma Bot (collegato a PostgreSQL)

### Configurazione

Crea `.env` con:
```
DB_PASSWORD=your_secure_password_here
BOT_TOKEN=your_telegram_bot_token
```

### Comandi Utili

```bash
# Avvia i servizi
docker-compose -f docker-compose-postgresql.yml up -d

# Vedi i log
docker-compose -f docker-compose-postgresql.yml logs -f aroma_bot

# Ferma i servizi
docker-compose -f docker-compose-postgresql.yml down

# Ferma e rimuovi anche i volumi (ATTENZIONE: cancella il database!)
docker-compose -f docker-compose-postgresql.yml down -v

# Backup del database
docker exec aroma_postgres pg_dump -U aroma_user aroma_bot > backup.sql

# Restore del database
docker exec -i aroma_postgres psql -U aroma_user aroma_bot < backup.sql
```

## Migrazione da SQLite a PostgreSQL in Docker

1. Esporta dati da SQLite (fuori dal container):
```bash
python3 migrate_python.py
```

2. Avvia Docker con PostgreSQL:
```bash
docker-compose -f docker-compose-postgresql.yml up -d
```

3. I dati saranno già nel database PostgreSQL!

## Note

- Il volume `postgres_data` persiste i dati del database
- PostgreSQL è accessibile sulla porta 5432
- Il bot si collega automaticamente a PostgreSQL tramite la rete Docker
