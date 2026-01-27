#!/bin/bash
# Script per cancellare e ricreare il database PostgreSQL

echo "🗑️  Cancellazione e ricreazione database PostgreSQL"
echo "===================================================="

# Chiedi conferma
read -p "Sei sicuro di voler cancellare il database aroma_bot? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operazione annullata."
    exit 0
fi

# Chiedi la nuova password
read -sp "Inserisci la nuova password per l'utente alan: " new_password
echo

# Esegui i comandi PostgreSQL
sudo -u postgres psql <<EOF
-- Disconnetti tutti gli utenti dal database
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'aroma_bot';

-- Cancella il database
DROP DATABASE IF EXISTS aroma_bot;

-- Cancella l'utente
DROP USER IF EXISTS alan;

-- Ricrea il database
CREATE DATABASE aroma_bot;

-- Ricrea l'utente con la nuova password
CREATE USER alan WITH PASSWORD '$new_password';

-- Dai tutti i permessi
GRANT ALL PRIVILEGES ON DATABASE aroma_bot TO alan;

-- Connetti al database
\c aroma_bot

-- Dai permessi sullo schema
GRANT ALL ON SCHEMA public TO alan;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO alan;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO alan;

\q
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database ricreato con successo!"
    echo ""
    echo "Credenziali:"
    echo "  Database: aroma_bot"
    echo "  Utente: alan"
    echo "  Password: $new_password"
    echo ""
    echo "Ora puoi eseguire: python3 migrate_python.py"
else
    echo ""
    echo "❌ Errore durante la ricreazione del database"
fi
