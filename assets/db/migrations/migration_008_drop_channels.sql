-- Migration 008: Drop obsolete channels table if exists

BEGIN;

DROP TABLE IF EXISTS public.channels CASCADE;

COMMIT;


