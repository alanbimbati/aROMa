#!/bin/bash
# Script di migrazione automatica da SQLite a PostgreSQL

echo "🚀 Migrazione da SQLite a PostgreSQL"
echo "===================================="

# 1. Verifica PostgreSQL installato
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL non installato!"
    echo "Installa con: sudo apt install postgresql postgresql-contrib"
    exit 1
fi

echo "✅ PostgreSQL trovato"

# 2. Verifica pgloader installato
if ! command -v pgloader &> /dev/null; then
    echo "⚠️  pgloader non trovato, installazione..."
    sudo apt install -y pgloader
fi

echo "✅ pgloader pronto"

# 3. Leggi credenziali
read -p "Nome database PostgreSQL [aroma_bot]: " DB_NAME
DB_NAME=${DB_NAME:-aroma_bot}

read -p "Utente PostgreSQL [aroma_user]: " DB_USER
DB_USER=${DB_USER:-aroma_user}

read -sp "Password PostgreSQL: " DB_PASSWORD
echo

# 4. Crea database e utente
echo "📦 Creazione database..."
sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF

if [ $? -eq 0 ]; then
    echo "✅ Database creato"
else
    echo "❌ Errore creazione database"
    exit 1
fi

# 5. Backup SQLite
echo "💾 Backup SQLite..."
cp points.db points.db.backup
echo "✅ Backup salvato in points.db.backup"

# 6. Migrazione dati
echo "🔄 Migrazione dati con pgloader..."
pgloader points.db "postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Dati migrati con successo"
else
    echo "❌ Errore durante migrazione"
    exit 1
fi

# 7. Crea file .env
echo "📝 Creazione file .env..."
cat > .env <<EOF
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
TEST_DB=0
EOF

echo "✅ File .env creato"

# 8. Installa dipendenze Python
echo "📦 Installazione dipendenze Python..."
pip install psycopg2-binary python-dotenv

echo ""
echo "✅ MIGRAZIONE COMPLETATA!"
echo "========================"
echo ""
echo "Prossimi passi:"
echo "1. Sostituisci database.py con database_postgresql.py:"
echo "   mv database.py database_sqlite.py.backup"
echo "   mv database_postgresql.py database.py"
echo ""
echo "2. Riavvia il bot:"
echo "   python3 main.py"
echo ""
echo "3. Verifica che tutto funzioni correttamente"
echo ""
echo "In caso di problemi, puoi tornare a SQLite:"
echo "   mv database_sqlite.py.backup database.py"
echo "   rm .env"
