-- Migration 001: Initial schema for Silent Study Tracker

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    total_seconds BIGINT DEFAULT 0,
    xp BIGINT DEFAULT 0,
    last_seen_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS voice_sessions (
    session_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_seconds INT,
    CONSTRAINT fk_voice_user
        FOREIGN KEY (user_id, guild_id) REFERENCES users(user_id, guild_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_streaks (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    streak_date DATE NOT NULL,
    PRIMARY KEY (user_id, guild_id, streak_date),
    CONSTRAINT fk_streak_user
        FOREIGN KEY (user_id, guild_id) REFERENCES users(user_id, guild_id)
        ON DELETE CASCADE
);


-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_guild ON voice_sessions(user_id, guild_id);
CREATE INDEX IF NOT EXISTS idx_streaks_user_guild ON daily_streaks(user_id, guild_id);

COMMIT;


