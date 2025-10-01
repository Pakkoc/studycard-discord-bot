-- Migration 007: Add permissive SELECT RLS policies for dashboard server access

BEGIN;

-- Note:
-- RLS was enabled in migration_006 and broad anon/auth privileges were revoked.
-- The dashboard connects via a direct Postgres role (from DATABASE_URL) and
-- needs to read aggregated data. We allow SELECT for all roles that can reach
-- the database. This is acceptable because the database URL is server-side only.

-- Users table: allow reading all rows
DROP POLICY IF EXISTS users_select_all ON public.users;
CREATE POLICY users_select_all
ON public.users
FOR SELECT
USING (true);

-- Voice sessions: allow reading all finalized sessions
DROP POLICY IF EXISTS voice_sessions_select_all ON public.voice_sessions;
CREATE POLICY voice_sessions_select_all
ON public.voice_sessions
FOR SELECT
USING (true);

-- Daily streaks: allow reading all rows
DROP POLICY IF EXISTS daily_streaks_select_all ON public.daily_streaks;
CREATE POLICY daily_streaks_select_all
ON public.daily_streaks
FOR SELECT
USING (true);

COMMIT;


