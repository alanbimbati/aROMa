#!/bin/bash
# Script per creare e configurare database di test PostgreSQL

DB_USER="alan"
PROD_DB="aroma_bot"
TEST_DB="aroma_bot_test"

echo "🧪 Creazione database di test PostgreSQL..."
echo ""

# Crea database di test (se non esiste)
echo "1️⃣ Creazione database $TEST_DB..."
psql -U "$DB_USER" -h localhost -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"
psql -U "$DB_USER" -h localhost -d postgres -c "CREATE DATABASE $TEST_DB;"

if [ $? -ne 0 ]; then
    echo "❌ Errore durante la creazione del database"
    exit 1
fi

echo "✅ Database $TEST_DB creato"
echo ""

# Copia schema e dati dal database di produzione
echo "2️⃣ Copia dati da $PROD_DB a $TEST_DB..."
pg_dump -U "$DB_USER" -h localhost -d "$PROD_DB" | psql -U "$DB_USER" -h localhost -d "$TEST_DB"

if [ $? -eq 0 ]; then
    echo "✅ Dati copiati con successo"
else
    echo "❌ Errore durante la copia dei dati"
    exit 1
fi

echo ""
echo "✅ Database di test pronto!"
echo ""
echo "📝 Per usare il database di test:"
echo ""
echo "1. Connessione via psql:"
echo "   psql -U $DB_USER -h localhost -d $TEST_DB"
echo ""
echo "2. Modifica .env per usare il test DB:"
echo "   DB_NAME=$TEST_DB"
echo ""
echo "3. Query SQL dirette:"
echo "   psql -U $DB_USER -h localhost -d $TEST_DB -c \"SELECT * FROM utente WHERE id_Telegram=62716473;\""
echo ""
echo "⚠️  IMPORTANTE: Ricordati di tornare a DB_NAME=$PROD_DB quando hai finito i test!"
