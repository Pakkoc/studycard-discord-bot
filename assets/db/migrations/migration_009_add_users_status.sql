-- Migration 009: Add users.status column to indicate membership presence

BEGIN;

-- Add status column if missing
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';

-- Ensure CHECK constraint exists (drop if exists, then create)
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_status_check;
ALTER TABLE public.users
  ADD CONSTRAINT users_status_check CHECK (status IN ('active','left'));

-- Index to filter by status quickly
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);

COMMIT;


