-- Migration: UTC 시간을 KST (+9시간)로 변환
-- 주의: 이 마이그레이션은 한 번만 실행해야 합니다!
-- 실행 전 반드시 백업을 권장합니다.

-- 1. users 테이블의 last_seen_at 컬럼 +9시간
UPDATE users
SET last_seen_at = last_seen_at + INTERVAL '9 hours'
WHERE last_seen_at IS NOT NULL;

-- 2. voice_sessions 테이블의 started_at, ended_at 컬럼 +9시간
UPDATE voice_sessions
SET
    started_at = started_at + INTERVAL '9 hours',
    ended_at = ended_at + INTERVAL '9 hours'
WHERE started_at IS NOT NULL;
