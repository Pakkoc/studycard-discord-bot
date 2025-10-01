# 🎓 마법사관학교 프로필 봇

Discord 서버에서 음성 채널 참여 시간을 추적하고, 학습자의 활동을 시각화한 프로필 카드를 슬래시 명령어로 제공하는 한국어 기반 Discord 봇입니다. Python `discord.py` 봇 + Next.js 대시보드(서버 렌더링) + Supabase(PostgreSQL)로 구성됩니다.

![alt text](<ex-image/예시 이미지.png>)
  
## ✨ 현재 제공 기능
- 슬래시 명령어: `/profile` (선택 매개변수: @사용자)
  - 본인 또는 지정한 사용자의 프로필 카드 이미지를 생성하여 전송합니다.
  - 포함 정보: 오늘/주/월/누적 학습시간, XP/레벨 진행도, 학번, 기숙사, 월간 스트릭 요약(캘린더 섹션)

참고: 기존 `/streak`, `/ping`, `/help`, `/level` 등은 제거되었습니다. 현재는 `/profile` 하나만 제공합니다.

## 🧩 작동 개요
- 음성 채널 입·퇴장 이벤트로 학습 세션을 기록합니다.
- 기록된 시간으로 누적 학습 시간과 XP/레벨을 계산합니다.
- 선택된 채널(옵션)에 게시글/포럼 작성 시 추가 XP를 부여할 수 있습니다.
- 레벨업 발생 시, 지정된 텍스트 채널로 자동 축하 메시지를 보냅니다(옵션).
- `/profile` 실행 시, DB 집계값을 사용해 프로필 카드 + 월간 통계 이미지를 생성합니다.

## 🚀 시작하기
### 1) 필수 조건
- Python 3.11+
- PostgreSQL 데이터베이스 (supabase)
- Discord Bot Token

### 2) 설치
```bash
# 저장소 클론
git clone https://github.com/Pakkoc/studycard-discord-bot.git
cd studycard-discord-bot

# 가상환경 생성
python -m venv .venv

# (Windows CMD)
.venv\Scripts\activate
# (macOS/Linux)
# source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3) 환경 변수 (.env)
프로젝트 루트에 `.env` 파일을 생성하고 아래 값을 설정하세요.
```env
# 필수
DISCORD_BOT_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://user:password@host:5432/dbname

# 선택: 게시/포럼 활동에 XP 부여 (쉼표로 채널 ID 나열)
POST_XP_CHANNEL_IDS=<CHANNEL_ID_1>,<CHANNEL_ID_2>
# 선택: 게시/포럼 활동 XP 수치/쿨다운(초) 설정
POST_XP_AMOUNT=3
POST_XP_COOLDOWN_SEC=60

# 선택: 슬래시 동기화 테스트용 단일 길드 ID
DEV_GUILD_ID=<GUILD_ID>

# 선택: 레벨업 축하 메시지를 보낼 채널 지정 (전역)
LEVELUP_CHANNEL_ID=<CHANNEL_ID>
# 참고: 길드별 변수 LEVELUP_CHANNEL_ID_<GUILD_ID>는 더 이상 사용하지 않습니다.
```

#### 권한 관련 설정
- 기본값: 역할명 "기숙사장"을 정확 일치로 검사합니다.
- 환경변수로 커스터마이즈 가능 (ID가 이름보다 우선):
```env
# 쉼표 구분 역할 ID 목록 (권장) — 예: 111111111111111111,222222222222222222
HOUSE_LEADER_ROLE_IDS=<ROLE_ID_1>,<ROLE_ID_2>

# 쉼표 구분 역할 이름 목록 (정확 일치) — 예: 기숙사장, House Lead
HOUSE_LEADER_ROLE_NAMES=기숙사장
```

#### 음성 세션 및 XP 정책
```env
# 음성 세션 최소 인정 시간(초)
VOICE_MIN_SESSION_SEC=180

# 시간당 XP 부여량 (신규) — 예: 1시간에 3XP 지급
XP_PER_HOUR=3

# (레거시) 포커스 시간(초) 당 1XP 기준값 — XP_PER_HOUR 미설정 시 사용
FOCUS_SECONDS_PER_XP=3600
```

#### 기숙사 판별 키워드 (역할명 포함 여부)
```env
# 형식: 키:라벨,키:라벨 ... (공백 무시)
# 예시: 소용돌이:소용돌이,펭도리야:펭도리야,노블레빗:노블레빗,볼리베어:볼리베어
HOUSE_PATTERNS=소용돌이:소용돌이,펭도리야:펭도리야,노블레빗:노블레빗,볼리베어:볼리베어
```

### 3-1) 대시보드(Next.js) 환경 변수
대시보드는 `pg`로 DB에 직접 연결합니다. 로컬은 `dashboard/.env.local`, Vercel 배포는 프로젝트 Settings → Environment Variables에 설정하세요.

필수:
```env
# Supabase Postgres Pooler(권장)로 연결하세요. 포트는 6543, sslmode=require
DATABASE_URL=postgresql://<user>:<pass>@<project>.pooler.supabase.com:6543/postgres?sslmode=require

# 조회할 길드 ID (DEFAULT_GUILD_ID 또는 DEV_GUILD_ID 중 하나)
DEV_GUILD_ID=<GUILD_ID>
# 또는
DEFAULT_GUILD_ID=<GUILD_ID>

# 선택: 빌드/테스트 시 데이터 페치 스킵(기본 비활성화)
SKIP_DASHBOARD_FETCH=0

# Vercel에서 TLS 체인 검증 오류가 발생할 때(SELF_SIGNED_CERT_IN_CHAIN) 중 하나로 해결
NODE_TLS_REJECT_UNAUTHORIZED=0    # 또는
PGSSLMODE=no-verify
```

확인 방법:
- 배포 후 `/api/stats?limit=5` 가 200으로 응답하면 정상 연결입니다.
- 500 + 로그에 `self-signed certificate in certificate chain` 이 보이면 위 TLS 완화 환경변수를 추가하세요.

### 4) 데이터베이스 마이그레이션
```bash
python scripts/migrate.py
```

### 5) 실행
```bash
python src/bot.py
```

### 6) 폰트 준비(서버에서 한글 깨짐 방지)
이미지 생성은 한글 폰트가 필요합니다. 아래 둘 중 하나로 준비하세요.

방법 A: 프로젝트에 폰트 포함(권장)
```bash
mkdir -p assets/fonts
curl -fL -o assets/fonts/NotoSansKR-Regular.ttf \
  https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf
```

방법 B: 서버에 시스템 폰트 설치 후 연결
```bash
sudo apt update && sudo apt install -y fonts-noto-cjk
ln -sf /usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc assets/fonts/NotoSansKR-Regular.ttf || true
```
`core/imaging.py`는 `assets/fonts/NotoSansKR-Regular.ttf/otf` → Windows `malgun.ttf` → Arial → PIL 기본 폰트 순으로 탐색합니다.

## 🧭 명령어
- `/profile [@사용자]`: 프로필 카드 생성 및 전송
  - 일반 사용자: 매개변수 없이 실행 → 본인 프로필만 조회 가능
  - 기숙사장 역할 보유자: `@사용자` 지정 시 타인 프로필 조회 가능 (역할명 정확히 "기숙사장")
  - 표시 정보: 서버 내 닉네임/별명, 학번(가입일 기반), 기숙사(역할명 패턴), 오늘/주/월/누적 학습시간, XP/레벨 진행도, 월간 스트릭 요약

## ☁️ 배포 가이드

### Supabase
- 프로젝트 생성 후 Project Settings → Database에서 Pooler 연결 문자열을 확인합니다.
- `assets/db/migrations`의 스크립트는 RLS 활성화와 읽기 정책을 포함합니다. `python scripts/migrate.py`로 적용하세요.

### 봇(백엔드) – Vultr Ubuntu + systemd
```bash
# 서버 준비
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

# 코드 배치 (예: /opt/profile-bot)
sudo mkdir -p /opt/profile-bot && cd /opt/profile-bot
sudo chown -R $USER:$USER /opt/profile-bot
git clone <YOUR_REPO_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 환경변수 파일
cat >/opt/profile-bot/.env <<'ENV'
DISCORD_BOT_TOKEN=...
DATABASE_URL=postgresql://...pooler.supabase.com:6543/postgres?sslmode=require
DEV_GUILD_ID=<GUILD_ID>
XP_PER_HOUR=1
VOICE_MIN_SESSION_SEC=180
ENV

# 마이그레이션
python scripts/migrate.py

# systemd 서비스
sudo tee /etc/systemd/system/profile-bot.service >/dev/null <<'UNIT'
[Unit]
Description=Discord Profile Bot (Python)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/profile-bot
EnvironmentFile=/opt/profile-bot/.env
ExecStart=/opt/profile-bot/.venv/bin/python src/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now profile-bot
sudo journalctl -u profile-bot -f
```

### 대시보드(프론트) – Vercel
1) Vercel에 프로젝트 Import → Root Directory: `dashboard`
2) Environment Variables(Production/Preview):
   - `DATABASE_URL` = Supabase Pooler URL(`…:6543/postgres?sslmode=require`)
   - `DEV_GUILD_ID` 또는 `DEFAULT_GUILD_ID` = 길드 ID
   - `SKIP_DASHBOARD_FETCH=0`
   - TLS 오류 시 `NODE_TLS_REJECT_UNAUTHORIZED=0` 또는 `PGSSLMODE=no-verify`
3) Deploy → `/api/stats?limit=5`로 연결 확인 → `/` 및 `/stats` 페이지 확인

## 🗂 프로젝트 구조 (요약)
```
profile_bot/
├── src/
│   └── bot.py              # 메인 봇 애플리케이션
├── cogs/
│   └── profile_cog.py      # /profile 명령어
├── core/
│   ├── database.py         # DB 연결/쿼리/집계
│   ├── imaging.py          # 프로필/통계 이미지 생성
│   └── leveling.py         # 레벨 계산 로직
├── assets/
│   └── db/migrations/      # DB 마이그레이션 SQL
├── scripts/                # 유틸리티 스크립트 (migrate 등)
└── vooster-docs/           # 프로젝트 문서 (PRD/아키텍처/가이드)
```

## 🛠 문제 해결(FAQ)
- Slash 명령어가 안 보임: `.env`의 `DEV_GUILD_ID`가 설정되어 있으면 해당 길드에만 즉시 동기화됩니다. ID가 다르면 보이지 않습니다. 제거하거나 올바른 ID로 재시작하세요.
- 디스코드에 ‘앱’만 보이고 ‘봇’이 없음: 초대 URL을 OAuth2 → URL Generator에서 `bot` + `applications.commands` Scopes로 다시 생성해 초대하세요.
- 대시보드가 500 에러/데이터 없음: Vercel Functions 로그에서 `self-signed certificate in certificate chain`이면 `NODE_TLS_REJECT_UNAUTHORIZED=0`(또는 `PGSSLMODE=no-verify`) 추가 후 재배포. DB는 반드시 Pooler(6543)로 연결.
- 프로필 이미지 한글 깨짐/폰트 달라짐: `assets/fonts/NotoSansKR-Regular.ttf`를 배치하거나 `fonts-noto-cjk` 설치.
- 봇이 오프라인: 토큰이 다른 애플리케이션 것일 수 있습니다. 로그의 `Logged in as ... (ID: ...)`가 Dev Portal Bot ID와 일치하는지 확인하고 `.env`의 `DISCORD_BOT_TOKEN`을 교체 후 재시작.

## 🔒 보안 주의
- `DISCORD_BOT_TOKEN`, `DATABASE_URL`은 절대 공개 저장소나 클라이언트에 노출하지 마세요.
- Supabase의 `SERVICE_ROLE_KEY`는 대시보드에서 사용하지 않습니다(브라우저에 노출 금지).

## 📚 추가 문서
자세한 기획/아키텍처/가이드 문서는 아래를 확인하세요.
- vooster-docs/prd.md
- vooster-docs/architecture.md
- vooster-docs/guideline.md
- vooster-docs/design-guide.md
- vooster-docs/ia.md
- vooster-docs/step-by-step.md
- vooster-docs/clean-code.md

## 📝 라이선스
이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE`를 참조하세요.

## 💬 문의
이슈나 문의는 저장소 이슈 트래커를 이용해 주세요.
