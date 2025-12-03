-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.daily_streaks (
  user_id bigint NOT NULL,
  guild_id bigint NOT NULL,
  streak_date date NOT NULL,
  CONSTRAINT daily_streaks_pkey PRIMARY KEY (user_id, guild_id, streak_date),
  CONSTRAINT fk_streak_user FOREIGN KEY (user_id) REFERENCES public.users(user_id),
  CONSTRAINT fk_streak_user FOREIGN KEY (guild_id) REFERENCES public.users(user_id),
  CONSTRAINT fk_streak_user FOREIGN KEY (user_id) REFERENCES public.users(guild_id),
  CONSTRAINT fk_streak_user FOREIGN KEY (guild_id) REFERENCES public.users(guild_id)
);
CREATE TABLE public.users (
  user_id bigint NOT NULL,
  guild_id bigint NOT NULL,
  total_seconds bigint DEFAULT 0,
  xp bigint DEFAULT 0,
  last_seen_at timestamp with time zone,
  nickname text,
  student_no character varying,
  status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'left'::text])),
  level integer NOT NULL DEFAULT 1,
  level_name text NOT NULL DEFAULT '마법학도'::text,
  CONSTRAINT users_pkey PRIMARY KEY (user_id, guild_id)
);
CREATE TABLE public.voice_sessions (
  session_id bigint NOT NULL DEFAULT nextval('voice_sessions_session_id_seq'::regclass),
  user_id bigint NOT NULL,
  guild_id bigint NOT NULL,
  started_at timestamp with time zone NOT NULL,
  ended_at timestamp with time zone,
  duration_seconds integer,
  CONSTRAINT voice_sessions_pkey PRIMARY KEY (session_id),
  CONSTRAINT fk_voice_user FOREIGN KEY (user_id) REFERENCES public.users(user_id),
  CONSTRAINT fk_voice_user FOREIGN KEY (guild_id) REFERENCES public.users(user_id),
  CONSTRAINT fk_voice_user FOREIGN KEY (user_id) REFERENCES public.users(guild_id),
  CONSTRAINT fk_voice_user FOREIGN KEY (guild_id) REFERENCES public.users(guild_id)
);