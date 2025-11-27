-- Migration: TIMESTAMPTZ를 TIMESTAMP로 변경 (한국시간 naive datetime 저장)
-- 주의: 이 마이그레이션은 migration_012_convert_utc_to_kst.sql 실행 후에 실행해야 합니다.
-- 이미 KST로 변환된 데이터가 있다고 가정합니다.

-- 1. voice_sessions 테이블
ALTER TABLE voice_sessions
    ALTER COLUMN started_at TYPE TIMESTAMP WITHOUT TIME ZONE,
    ALTER COLUMN ended_at TYPE TIMESTAMP WITHOUT TIME ZONE;

-- 2. users 테이블
ALTER TABLE users
    ALTER COLUMN last_seen_at TYPE TIMESTAMP WITHOUT TIME ZONE;
