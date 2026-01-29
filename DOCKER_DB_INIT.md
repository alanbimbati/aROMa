# Docker Database Initialization Guide

## Problem
When you run `docker-compose up` for the first time, the PostgreSQL database is empty - it has no tables. This causes errors like:
```
relation "mob" does not exist
relation "game_event" does not exist
```

## Solutions

### Option 1: Quick Setup (Recommended)
Copy schema from your existing test database:

```bash
# Export schema from test DB
PGPASSWORD=asd1XD2LoL3 pg_dump -h localhost -U alan -d aroma_bot_test \
  --schema-only --no-owner --no-acl > schema.sql

# Import to Docker
docker-compose exec -T postgres psql -U alan -d aroma_bot < schema.sql

# Verify
docker-compose exec postgres psql -U alan -d aroma_bot -c "\dt"
```

### Option 2: Create from Python Models
Let SQLAlchemy create the tables:

```bash
docker-compose exec aroma_bot python3 -c \
  "from database import Database, Base; \
   db = Database(); \
   Base.metadata.create_all(db.engine); \
   print('✅ Tables created!')"
```

### Option 3: Import Full Database Dump
If you have data to import:

```bash
# Export from test DB (with data)
PGPASSWORD=asd1XD2LoL3 pg_dump -h localhost -U alan -d aroma_bot_test \
  --no-owner --no-acl > full_dump.sql

# Import to Docker
docker-compose exec -T postgres psql -U alan -d aroma_bot < full_dump.sql
```

## Automated Setup

I've created helper scripts:

### `init_docker_db.sh`
Interactive script that guides you through database initialization.

```bash
./init_docker_db.sh
```

### `quick_docker_setup.sh`
Automatically exports from test DB and imports to Docker (requires password).

```bash
./quick_docker_setup.sh
```

## Adding to docker-compose.yml

For automatic initialization on first run, add an init script:

1. Create `init-db.sh`:
```bash
#!/bin/bash
set -e

# This runs only if database is empty
if [ ! -f /var/lib/postgresql/data/initialized ]; then
    echo "Initializing database..."
    # Add your initialization commands here
    touch /var/lib/postgresql/data/initialized
fi
```

2. Update `docker-compose.yml`:
```yaml
postgres:
  volumes:
    - ./init-db.sh:/docker-entrypoint-initdb.d/init-db.sh
```

## Troubleshooting

### "relation does not exist" errors
Database is empty. Run one of the solutions above.

### "password authentication failed"
Check your `.env` file has correct `DB_PASSWORD`.

### Tables exist but no data
You imported schema-only. To import data:
```bash
PGPASSWORD=asd1XD2LoL3 pg_dump -h localhost -U alan -d aroma_bot_test \
  --data-only --no-owner --no-acl > data.sql
docker-compose exec -T postgres psql -U alan -d aroma_bot < data.sql
```

### Want to start fresh
```bash
docker-compose down -v  # -v removes volumes (deletes data!)
docker-compose up -d
# Then initialize database again
```

## Best Practice for Production

1. **Keep schema.sql in git**: Export your schema and commit it
2. **Use migrations**: Consider using Alembic for schema changes
3. **Backup regularly**: Use `pg_dump` to backup production data
4. **Separate test/prod data**: Never import test data to production

## Quick Reference

```bash
# Check if tables exist
docker-compose exec postgres psql -U alan -d aroma_bot -c "\dt"

# View specific table
docker-compose exec postgres psql -U alan -d aroma_bot -c "\d mob"

# Count records
docker-compose exec postgres psql -U alan -d aroma_bot -c "SELECT COUNT(*) FROM utente"

# Drop all tables (CAREFUL!)
docker-compose exec postgres psql -U alan -d aroma_bot -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```
