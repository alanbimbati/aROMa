#!/bin/bash

# Configuration
REMOTE_USER="dietpi"
REMOTE_HOST="192.168.1.21"
REMOTE_DB="aroma_bot"
REMOTE_DB_USER="alan"
BACKUP_FILE="aroma_prod_backup.sql"
LOCAL_DB="aroma_bot_test"

echo "Step 1: Creating backup on remote server (DietPi) via aroma_postgres container..."
# We use aroma_postgres because that's the container with the DB engine
# We also ensure the container is started if it was stopped
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd Bot/aroma && sudo docker compose up -d postgres && sudo docker exec aroma_postgres pg_dump -U ${REMOTE_DB_USER} ${REMOTE_DB} > ~/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "Step 2: Transferring backup to local machine..."
    mkdir -p ./dumps
    scp ${REMOTE_USER}@${REMOTE_HOST}:~/${BACKUP_FILE} ./dumps/aroma_prod_backup.sql
    
    if [ $? -eq 0 ]; then
        echo "Step 3: Restoring to local database (${LOCAL_DB})..."
        # Terminate active connections to the local database to allow dropping it
        echo "Terminating local connections to ${LOCAL_DB}..."
        psql -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${LOCAL_DB}' AND pid <> pg_backend_pid();"
        
        dropdb ${LOCAL_DB} --if-exists
        createdb ${LOCAL_DB}
        psql -d ${LOCAL_DB} < ./dumps/aroma_prod_backup.sql
        
        echo "Step 4: Running Alembic migrations to align schema..."
        export TEST_DB=1 # Ensure it targets the test/dev DB as per .env
        alembic upgrade head
        
        echo "✅ Sync and Migration completed successfully!"
    else
        echo "❌ Failed to transfer the backup."
    fi
else
    echo "❌ Failed to create backup on remote server. Check if aroma_postgres container is running."
fi
