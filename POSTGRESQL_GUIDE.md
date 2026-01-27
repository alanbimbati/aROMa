# Guida PostgreSQL - Backup, Test e Query SQL

## 📦 Backup del Database

### Backup Automatico
```bash
chmod +x backup_postgresql.sh
./backup_postgresql.sh
```

Questo crea un backup compresso in `backups/aroma_bot_YYYYMMDD_HHMMSS.sql.gz`

### Backup Manuale
```bash
# Backup completo
pg_dump -U alan -h localhost -d aroma_bot -F p -f backup.sql

# Backup compresso
pg_dump -U alan -h localhost -d aroma_bot | gzip > backup.sql.gz

# Solo schema (senza dati)
pg_dump -U alan -h localhost -d aroma_bot --schema-only -f schema.sql

# Solo dati (senza schema)
pg_dump -U alan -h localhost -d aroma_bot --data-only -f data.sql
```

## 🧪 Database di Test

### Creazione Database di Test
```bash
chmod +x create_test_db.sh
./create_test_db.sh
```

Questo crea `aroma_bot_test` con una copia completa dei dati di produzione.

### Usare il Database di Test

**Opzione 1: Modifica temporanea .env**
```bash
# Modifica .env
DB_NAME=aroma_bot_test

# Esegui il bot
python3 main.py

# Ricordati di tornare a:
DB_NAME=aroma_bot
```

**Opzione 2: Connessione diretta con psql**
```bash
psql -U alan -h localhost -d aroma_bot_test
```

## 🔧 Query SQL Dirette

### Connessione al Database
```bash
# Database di produzione
psql -U alan -h localhost -d aroma_bot

# Database di test
psql -U alan -h localhost -d aroma_bot_test
```

### Query Utili per il Tuo Profilo

**Visualizza il tuo profilo completo:**
```sql
SELECT * FROM utente WHERE id_Telegram = 62716473;
```

**Modifica EXP e livello:**
```sql
UPDATE utente 
SET exp = 999999, livello = 99 
WHERE id_Telegram = 62716473;
```

**Aggiungi Wumpa (soldi):**
```sql
UPDATE utente 
SET money = money + 100000 
WHERE id_Telegram = 62716473;
```

**Modifica statistiche:**
```sql
UPDATE utente 
SET 
    max_health = 9999,
    current_hp = 9999,
    max_mana = 9999,
    current_mana = 9999,
    base_damage = 500,
    resistance = 75,
    crit_chance = 50,
    speed = 100
WHERE id_Telegram = 62716473;
```

**Aggiungi punti stat:**
```sql
UPDATE utente 
SET stat_points = 999 
WHERE id_Telegram = 62716473;
```

**Diventa premium:**
```sql
UPDATE utente 
SET 
    premium = 1,
    scadenza_premium = NOW() + INTERVAL '1 year',
    abbonamento_attivo = 1
WHERE id_Telegram = 62716473;
```

**Sblocca tutti i personaggi:**
```sql
-- Vedi personaggi disponibili
SELECT id, name FROM character_ownership;

-- Sblocca un personaggio specifico
INSERT INTO user_character (user_id, character_id, unlocked_at)
VALUES (62716473, 1, NOW())
ON CONFLICT DO NOTHING;
```

**Visualizza achievement:**
```sql
-- Vedi tutti gli achievement
SELECT * FROM achievement;

-- Vedi i tuoi achievement
SELECT a.name, a.description, ua.progress, ua.unlocked_at
FROM user_achievement ua
JOIN achievement a ON ua.achievement_id = a.id
WHERE ua.user_id = 62716473;

-- Sblocca un achievement
UPDATE user_achievement
SET progress = 100, unlocked_at = NOW()
WHERE user_id = 62716473 AND achievement_id = 1;
```

### Comandi psql Utili

Dentro `psql`:

```sql
-- Lista tutte le tabelle
\dt

-- Descrivi struttura tabella
\d utente

-- Esci
\q

-- Esegui query da file
\i query.sql

-- Mostra query in formato esteso (più leggibile)
\x

-- Cronologia comandi
\s

-- Aiuto
\?
```

### Query da Terminale (senza entrare in psql)

```bash
# Singola query
psql -U alan -h localhost -d aroma_bot_test -c "SELECT nome, livello, exp FROM utente WHERE id_Telegram = 62716473;"

# Query da file
psql -U alan -h localhost -d aroma_bot_test -f my_queries.sql

# Output in formato CSV
psql -U alan -h localhost -d aroma_bot_test -c "SELECT * FROM utente;" --csv > users.csv
```

## 🔄 Ripristino Backup

### Ripristino Automatico
```bash
chmod +x restore_postgresql.sh
./restore_postgresql.sh backups/aroma_bot_20260127_143000.sql.gz
```

### Ripristino Manuale
```bash
# Da file .sql
psql -U alan -h localhost -d aroma_bot -f backup.sql

# Da file .sql.gz
gunzip -c backup.sql.gz | psql -U alan -h localhost -d aroma_bot
```

## ⚠️ Best Practices

1. **Fai sempre un backup prima di modifiche importanti**
   ```bash
   ./backup_postgresql.sh
   ```

2. **Testa su database di test prima**
   ```bash
   ./create_test_db.sh
   # Modifica .env: DB_NAME=aroma_bot_test
   # Fai i tuoi test
   # Torna a: DB_NAME=aroma_bot
   ```

3. **Usa transazioni per modifiche multiple**
   ```sql
   BEGIN;
   UPDATE utente SET exp = 999999 WHERE id_Telegram = 62716473;
   UPDATE utente SET money = 100000 WHERE id_Telegram = 62716473;
   -- Se tutto ok:
   COMMIT;
   -- Se qualcosa va male:
   -- ROLLBACK;
   ```

4. **Verifica sempre le modifiche**
   ```sql
   -- Prima della modifica
   SELECT exp, money FROM utente WHERE id_Telegram = 62716473;
   
   -- Fai la modifica
   UPDATE utente SET exp = 999999 WHERE id_Telegram = 62716473;
   
   -- Verifica dopo
   SELECT exp, money FROM utente WHERE id_Telegram = 62716473;
   ```

## 📊 Monitoring

### Dimensione Database
```bash
psql -U alan -h localhost -d postgres -c "SELECT pg_size_pretty(pg_database_size('aroma_bot'));"
```

### Tabelle più grandi
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
```

### Numero righe per tabella
```sql
SELECT 
    schemaname,
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```
