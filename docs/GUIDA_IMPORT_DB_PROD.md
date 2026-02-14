# Guida all'Importazione Database in Produzione

Questa guida spiega come importare il file `aroma_bot_prod_ready.sql.gz` (appena generato) sul server di produzione (DietPi).

## 1. Trasferire il dump sul server
Esegui questo comando dal tuo terminale locale (nella cartella del progetto):

```bash
scp aroma_bot_prod_ready.sql.gz dietpi@192.168.1.21:~/Bot/aroma/backups/
```

### Opzione A: Comandi Docker (Consigliato se psql non è installato sul host)
Dato che il database gira in Docker, usa questi comandi che non richiedono l'installazione di PostgreSQL sul server host:

```bash
# Entra nel server
ssh dietpi@192.168.1.21
cd ~/Bot/aroma

# Ferma il bot
docker compose stop aroma_bot

# Decomprimi il dump in una cartella temporanea
gunzip -k backups/aroma_bot_prod_ready.sql.gz -c > restore.sql

# Ricrea il database usando psql DENTRO il container
docker compose exec -T postgres psql -U alan -d postgres -c "DROP DATABASE IF EXISTS aroma_bot;"
docker compose exec -T postgres psql -U alan -d postgres -c "CREATE DATABASE aroma_bot;"

# Importa i dati passando il file allo standard input del container
cat restore.sql | docker compose exec -T postgres psql -U alan -d aroma_bot

# Rimuovi il file temporaneo e riavvia
rm restore.sql
docker compose start aroma_bot
```

## 3. Verifica
Dopo il riavvio, controlla che il bot veda i nuovi dati:
```bash
docker compose exec postgres psql -U alan -d aroma_bot -c "SELECT COUNT(*) FROM utente;"
```

---
*Documentazione creata il 14/02/2026*
