-- Migration 006: Enable RLS and revoke anon/authenticated privileges on public tables

BEGIN;

-- Revoke broad access from anon/authenticated roles (PostgREST clients)
REVOKE ALL ON TABLE public.users FROM anon, authenticated;
REVOKE ALL ON TABLE public.daily_streaks FROM anon, authenticated;
REVOKE ALL ON TABLE public.voice_sessions FROM anon, authenticated;

-- Ensure RLS is enabled on the core tables
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.daily_streaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.voice_sessions ENABLE ROW LEVEL SECURITY;

COMMIT;


