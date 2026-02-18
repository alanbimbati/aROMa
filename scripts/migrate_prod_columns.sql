-- Migration: add columns missing in production
-- Run with:
--   docker compose exec -T postgres psql -U alan -d aroma_bot < scripts/migrate_prod_columns.sql

ALTER TABLE utente ADD COLUMN IF NOT EXISTS transformation_expires_at TIMESTAMP;
ALTER TABLE utente ADD COLUMN IF NOT EXISTS current_transformation VARCHAR(100);
ALTER TABLE utente ADD COLUMN IF NOT EXISTS current_mount_id INTEGER;
ALTER TABLE utente ADD COLUMN IF NOT EXISTS meditating_until TIMESTAMP;
ALTER TABLE utente ADD COLUMN IF NOT EXISTS last_egg_nurture TIMESTAMP;

-- Confirm
SELECT column_name FROM information_schema.columns
WHERE table_name = 'utente'
  AND column_name IN (
    'transformation_expires_at',
    'current_transformation',
    'current_mount_id',
    'meditating_until',
    'last_egg_nurture'
  )
ORDER BY column_name;
