# Guida all'Importazione Database in Produzione

Questa guida spiega come importare il file `aroma_bot_prod_ready.sql.gz` (appena generato) sul server di produzione (DietPi).

## 1. Trasferire il dump sul server
Esegui questo comando dal tuo terminale locale (nella cartella del progetto):

```bash
scp aroma_bot_prod_ready.sql.gz dietpi@192.168.1.21:~/Bot/aroma/backups/
```

## 2. Eseguire il ripristino sul server
Puoi usare lo script di ripristino esistente o eseguire i comandi manualmente.

### Opzione A: Usare lo script (Consigliato)
Accedi in SSH al server e lancia lo script fornendo il nome del file:

```bash
ssh dietpi@192.168.1.21
cd ~/Bot/aroma
./restore_backup.sh aroma_bot_prod_ready.sql.gz
```

> [!NOTE]
> Lo script fermerà il bot automaticamente, ricreerà il database e lo riavvierà al termine.

### Opzione B: Comandi manuali (Via Docker)
Se preferisci farlo passo dopo passo:

```bash
# Entra nel server
ssh dietpi@192.168.1.21
cd ~/Bot/aroma

# Ferma il bot
docker compose stop aroma_bot

# Decomprimi il dump
gunzip -c backups/aroma_bot_prod_ready.sql.gz > /tmp/restore.sql

# Ricrea il database
docker compose exec -T postgres psql -U alan -d postgres -c "DROP DATABASE IF EXISTS aroma_bot;"
docker compose exec -T postgres psql -U alan -d postgres -c "CREATE DATABASE aroma_bot;"

# Importa i dati
docker compose exec -T postgres psql -U alan -d aroma_bot < /tmp/restore.sql

# Riavvia il bot
docker compose start aroma_bot
```

## 3. Verifica
Dopo il riavvio, controlla che il bot veda i nuovi dati:
```bash
docker compose exec postgres psql -U alan -d aroma_bot -c "SELECT COUNT(*) FROM utente;"
```

---
*Documentazione creata il 14/02/2026*
