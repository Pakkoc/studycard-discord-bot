-- Migration 003: Drop users.language column (i18n removed)

BEGIN;

ALTER TABLE IF EXISTS users
    DROP COLUMN IF EXISTS language;

COMMIT;



