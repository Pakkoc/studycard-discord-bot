-- Migration 005: Add student_no column to users table

BEGIN;

ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS student_no VARCHAR(8);

-- Optional index to query by guild/student_no if needed later
-- CREATE INDEX IF NOT EXISTS idx_users_guild_student_no ON users(guild_id, student_no);

COMMIT;



