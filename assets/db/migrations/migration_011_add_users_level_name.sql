-- Migration 011: Add users.level_name to store localized level title

BEGIN;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS level_name TEXT NOT NULL DEFAULT '마법학도';

CREATE INDEX IF NOT EXISTS idx_users_level_name ON public.users(level_name);

COMMIT;


