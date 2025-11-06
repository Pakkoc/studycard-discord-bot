-- Migration 010: Add users.level to store current level number (1..10)

BEGIN;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS level INT NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_users_level ON public.users(level);

COMMIT;


