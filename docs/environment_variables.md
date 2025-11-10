# 환경 변수 설정 가이드

이 문서는 봇을 설정하기 위한 모든 환경 변수를 설명합니다.

## 필수 환경 변수

### DISCORD_BOT_TOKEN
- **설명**: 디스코드 봇 토큰
- **필수 여부**: ✅ 필수
- **예시**: `DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN`

### DATABASE_URL
- **설명**: PostgreSQL 데이터베이스 연결 URL
- **필수 여부**: ✅ 필수
- **형식**: `postgresql://user:password@host:5432/database`
- **예시**: `DATABASE_URL=postgresql://myuser:mypass@localhost:5432/magicschool`

## 선택적 환경 변수

### 개발 설정

#### DEV_GUILD_ID
- **설명**: 개발 중 빠른 명령어 동기화를 위한 길드 ID
- **필수 여부**: ❌ 선택
- **예시**: `DEV_GUILD_ID=1234567890123456789`
- **참고**: 설정하지 않으면 전역 동기화를 사용합니다

### 음성 세션 설정

#### VOICE_MIN_SESSION_SEC
- **설명**: 기록할 최소 음성 세션 시간 (초)
- **필수 여부**: ❌ 선택
- **기본값**: `180` (3분)
- **예시**: `VOICE_MIN_SESSION_SEC=300`
- **참고**: 이 시간보다 짧은 세션은 기록되지 않습니다

#### EXCLUDED_VOICE_CHANNEL_IDS
- **설명**: 학습 시간 기록에서 제외할 음성 채널 ID 목록
- **필수 여부**: ❌ 선택
- **형식**: 콤마로 구분된 채널 ID 목록
- **예시**: `EXCLUDED_VOICE_CHANNEL_IDS=1234567890,9876543210`
- **사용 방법**:
  1. 디스코드에서 개발자 모드 활성화 (설정 > 고급 > 개발자 모드)
  2. 제외할 음성 채널 우클릭 → "ID 복사"
  3. 복사한 ID를 환경 변수에 추가 (여러 채널은 콤마로 구분)
  4. 봇 재시작
- **적용 효과**:
  - 제외된 채널에 입장해도 학습 시간이 기록되지 않음
  - 제외된 채널에서 다른 채널로 이동 시, 제외된 채널의 시간은 기록되지 않음
  - 일반 채널에서 제외된 채널로 이동 시, 일반 채널의 시간만 기록됨

### 레벨업 메시지 설정

#### LEVELUP_CHANNEL_ID
- **설명**: 레벨업 메시지를 보낼 채널 ID
- **필수 여부**: ❌ 선택
- **예시**: `LEVELUP_CHANNEL_ID=1234567890123456789`
- **참고**: 설정하지 않으면 시스템 채널 또는 첫 번째 텍스트 채널을 사용합니다

#### LEVELUP_MESSAGE_DELETE_AFTER_SEC
- **설명**: 레벨업 메시지를 자동 삭제할 시간 (초)
- **필수 여부**: ❌ 선택
- **기본값**: `0` (삭제하지 않음)
- **예시**: `LEVELUP_MESSAGE_DELETE_AFTER_SEC=30`

### 게시글 XP 설정

#### POST_XP_CHANNEL_IDS
- **설명**: 게시글 작성 시 XP를 부여할 채널 ID 목록
- **필수 여부**: ❌ 선택
- **형식**: 콤마로 구분된 채널 ID 목록
- **예시**: `POST_XP_CHANNEL_IDS=1234567890,9876543210`

#### POST_XP_AMOUNT
- **설명**: 게시글 작성 시 부여할 XP 양
- **필수 여부**: ❌ 선택
- **기본값**: `3`
- **예시**: `POST_XP_AMOUNT=5`

#### POST_XP_COOLDOWN_SEC
- **설명**: 게시글 XP 부여 쿨다운 시간 (초)
- **필수 여부**: ❌ 선택
- **기본값**: `60`
- **예시**: `POST_XP_COOLDOWN_SEC=120`

### 멤버 탈퇴 설정

#### LEAVE_DELETE_THRESHOLD_SEC
- **설명**: 이 시간 이하의 총 학습 시간을 가진 멤버가 탈퇴하면 모든 데이터 삭제 (초)
- **필수 여부**: ❌ 선택
- **기본값**: `1800` (30분)
- **예시**: `LEAVE_DELETE_THRESHOLD_SEC=3600`

#### RESET_USER_STATS_ON_LEAVE
- **설명**: 멤버 탈퇴 시 통계 초기화 여부
- **필수 여부**: ❌ 선택
- **기본값**: `0` (초기화하지 않음)
- **값**: `0` (비활성화) 또는 `1` (활성화)
- **예시**: `RESET_USER_STATS_ON_LEAVE=1`

### 기숙사 설정

#### HOUSE_PATTERNS
- **설명**: 역할 이름에서 기숙사를 매칭하는 패턴
- **필수 여부**: ❌ 선택
- **형식**: `키:라벨,키:라벨` (콤마로 구분)
- **기본값**: `소용돌이:소용돌이,펭도리야:펭도리야,노블레빗:노블레빗,볼리베어:볼리베어`
- **예시**: `HOUSE_PATTERNS=그리핀도르:그리핀도르,슬리데린:슬리데린`

#### SCHOLAR_ROLE_KEYWORDS
- **설명**: 장학생 배지를 표시할 역할 이름 키워드 (부분 일치)
- **필수 여부**: ❌ 선택
- **형식**: 콤마로 구분된 키워드 목록
- **기본값**: `장학생`
- **예시**: `SCHOLAR_ROLE_KEYWORDS=장학생,슈퍼장학생`

### 기숙사장 권한 설정

#### HOUSE_LEADER_ROLE_IDS
- **설명**: 기숙사장 권한을 가질 역할 ID 목록 (최우선)
- **필수 여부**: ❌ 선택
- **형식**: 콤마로 구분된 역할 ID 목록
- **예시**: `HOUSE_LEADER_ROLE_IDS=1234567890,9876543210`

#### HOUSE_LEADER_ROLE_NAMES
- **설명**: 기숙사장 권한을 가질 역할 이름 목록 (정확히 일치)
- **필수 여부**: ❌ 선택
- **형식**: 콤마로 구분된 역할 이름 목록
- **기본값**: `기숙사장`
- **예시**: `HOUSE_LEADER_ROLE_NAMES=기숙사장,관리자`

## .env 파일 예시

```bash
# 필수 설정
DISCORD_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:password@host:5432/database

# 음성 세션 설정
VOICE_MIN_SESSION_SEC=180
EXCLUDED_VOICE_CHANNEL_IDS=1234567890,9876543210

# 레벨업 메시지
LEVELUP_CHANNEL_ID=1234567890123456789
LEVELUP_MESSAGE_DELETE_AFTER_SEC=30

# 게시글 XP
POST_XP_CHANNEL_IDS=1234567890,9876543210
POST_XP_AMOUNT=3
POST_XP_COOLDOWN_SEC=60

# 멤버 탈퇴
LEAVE_DELETE_THRESHOLD_SEC=1800
RESET_USER_STATS_ON_LEAVE=0

# 기숙사 설정
HOUSE_PATTERNS=소용돌이:소용돌이,펭도리야:펭도리야,노블레빗:노블레빗,볼리베어:볼리베어
SCHOLAR_ROLE_KEYWORDS=장학생
HOUSE_LEADER_ROLE_IDS=
HOUSE_LEADER_ROLE_NAMES=기숙사장
```

## 설정 적용 방법

1. 프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다
2. 위의 환경 변수를 복사하여 필요한 값을 입력합니다
3. 봇을 재시작하면 설정이 적용됩니다

## 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요 (`.gitignore`에 포함되어 있음)
- 봇 토큰과 데이터베이스 비밀번호는 안전하게 보관하세요
- 환경 변수 변경 후에는 반드시 봇을 재시작해야 합니다

