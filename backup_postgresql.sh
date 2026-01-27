#!/bin/bash
# Script per creare backup del database PostgreSQL

# Configurazione
DB_NAME="aroma_bot"
DB_USER="alan"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/aroma_bot_${TIMESTAMP}.sql"

# Crea directory backups se non esiste
mkdir -p "$BACKUP_DIR"

echo "🔄 Creazione backup PostgreSQL..."
echo "Database: $DB_NAME"
echo "File: $BACKUP_FILE"
echo ""

# Crea backup con pg_dump
pg_dump -U "$DB_USER" -h localhost -d "$DB_NAME" -F p -f "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Comprimi il backup
    gzip "$BACKUP_FILE"
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    
    echo "✅ Backup completato!"
    echo "📁 File: ${BACKUP_FILE}.gz"
    echo "📊 Dimensione: $BACKUP_SIZE"
    echo ""
    echo "Per ripristinare questo backup:"
    echo "  gunzip ${BACKUP_FILE}.gz"
    echo "  psql -U $DB_USER -h localhost -d $DB_NAME -f $BACKUP_FILE"
else
    echo "❌ Errore durante il backup"
    exit 1
fi

# Mostra ultimi 5 backup
echo ""
echo "📋 Ultimi backup disponibili:"
ls -lht "$BACKUP_DIR" | head -6
