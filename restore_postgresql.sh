#!/bin/bash
# Script per ripristinare un backup PostgreSQL

if [ -z "$1" ]; then
    echo "❌ Errore: specifica il file di backup"
    echo ""
    echo "Uso: $0 <backup_file.sql.gz>"
    echo ""
    echo "Backup disponibili:"
    ls -lht backups/ | head -10
    exit 1
fi

BACKUP_FILE="$1"
DB_NAME="aroma_bot"
DB_USER="alan"

# Verifica che il file esista
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ File non trovato: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ATTENZIONE: Stai per sovrascrivere il database $DB_NAME"
echo "Backup: $BACKUP_FILE"
echo ""
read -p "Sei sicuro? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Ripristino annullato"
    exit 0
fi

# Decomprimi se necessario
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "📦 Decompressione backup..."
    gunzip -k "$BACKUP_FILE"
    SQL_FILE="${BACKUP_FILE%.gz}"
else
    SQL_FILE="$BACKUP_FILE"
fi

echo ""
echo "🔄 Ripristino database..."

# Disconnetti tutti gli utenti
psql -U "$DB_USER" -h localhost -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';"

# Drop e ricrea database
psql -U "$DB_USER" -h localhost -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
psql -U "$DB_USER" -h localhost -d postgres -c "CREATE DATABASE $DB_NAME;"

# Ripristina backup
psql -U "$DB_USER" -h localhost -d "$DB_NAME" -f "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database ripristinato con successo!"
    
    # Rimuovi file decompresso se era .gz
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        rm "$SQL_FILE"
    fi
else
    echo ""
    echo "❌ Errore durante il ripristino"
    exit 1
fi
