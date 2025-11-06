-- Migration 004: Add nickname column to users table

BEGIN;

ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS nickname TEXT;

COMMIT;



