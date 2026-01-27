#!/bin/bash
# Script per configurare PostgreSQL per Aroma Bot

echo "🔧 Configurazione PostgreSQL per Aroma Bot"
echo "=========================================="

# Connetti a PostgreSQL come utente postgres
sudo -u postgres psql <<EOF
-- Crea il database
CREATE DATABASE aroma_bot;

-- Crea l'utente (cambia la password!)
CREATE USER alan WITH PASSWORD 'your_secure_password_here';

-- Dai tutti i permessi all'utente
GRANT ALL PRIVILEGES ON DATABASE aroma_bot TO alan;

-- Connetti al database aroma_bot
\c aroma_bot

-- Dai permessi sullo schema public
GRANT ALL ON SCHEMA public TO alan;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO alan;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO alan;

-- Esci
\q
EOF

echo ""
echo "✅ PostgreSQL configurato!"
echo ""
echo "Credenziali:"
echo "  Database: aroma_bot"
echo "  Utente: alan"
echo "  Password: your_secure_password_here"
echo ""
echo "⚠️  IMPORTANTE: Cambia 'your_secure_password_here' con una password sicura!"
echo ""
echo "Ora puoi eseguire: python3 migrate_python.py"
