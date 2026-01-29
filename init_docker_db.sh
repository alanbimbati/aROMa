#!/bin/bash
# Initialize PostgreSQL database schema for Docker
# This script should be run once when setting up a new Docker environment

set -e

echo "🗄️  Initializing PostgreSQL Database Schema..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U alan -d aroma_bot; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "✅ PostgreSQL is ready!"

# Check if we have a schema file
if [ -f "schema.sql" ]; then
    echo "📋 Found schema.sql, applying schema..."
    docker-compose exec -T postgres psql -U alan -d aroma_bot < schema.sql
    echo "✅ Schema applied successfully!"
elif [ -f "database_schema.sql" ]; then
    echo "📋 Found database_schema.sql, applying schema..."
    docker-compose exec -T postgres psql -U alan -d aroma_bot < database_schema.sql
    echo "✅ Schema applied successfully!"
else
    echo "⚠️  No schema file found!"
    echo ""
    echo "Options:"
    echo "1. Create tables from Python models:"
    echo "   docker-compose exec aroma_bot python3 -c 'from database import Database, Base; db = Database(); Base.metadata.create_all(db.engine)'"
    echo ""
    echo "2. Import from existing database dump:"
    echo "   docker-compose exec -T postgres psql -U alan -d aroma_bot < your_dump.sql"
    echo ""
    echo "3. Copy schema from existing database:"
    echo "   pg_dump -h localhost -U alan -d aroma_bot_test --schema-only > schema.sql"
    echo "   Then run this script again"
    
    read -p "Do you want to create tables from Python models now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating tables from Python models..."
        docker-compose exec aroma_bot python3 -c "from database import Database, Base; db = Database(); Base.metadata.create_all(db.engine); print('✅ Tables created!')"
    fi
fi

echo ""
echo "🎉 Database initialization complete!"
echo ""
echo "To verify, run:"
echo "docker-compose exec postgres psql -U alan -d aroma_bot -c '\dt'"
