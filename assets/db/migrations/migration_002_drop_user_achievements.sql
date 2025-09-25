-- Migration 002: Drop user_achievements table (feature removed)

BEGIN;

DROP TABLE IF EXISTS user_achievements;

COMMIT;



