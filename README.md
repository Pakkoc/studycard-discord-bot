# 🎓 마법사관학교 프로필 봇

Discord 서버에서 음성 채널 참여 시간을 추적하고, 학습자들의 활동을 시각화하는 한국어 기반 Discord 봇입니다.

## ✨ 주요 기능

### 📊 프로필 시스템
- **학생증 스타일 프로필 카드**: 이름, 기숙사, 학번, 레벨 표시
- **경험치 시스템**: 음성 채널 1시간 참여 = 1XP
- **레벨 시스템**: 10단계 레벨 (견습마법사 → 현자)
- **기숙사 시스템**: 노블래빗🐇, 소용돌이🦋, 볼리베어🐻‍❄️, 펭도리아🐧

### 📅 스트릭 캘린더
- 최근 30일간의 활동 기록을 달력 형태로 시각화
- 연속 참여일 추적 및 표시

### 📚 특별 채널 보너스
- 마법도서관 채널에서 메시지 작성 시 3XP 추가 지급

## 🚀 시작하기

### 필요 조건
- Python 3.11+
- PostgreSQL 데이터베이스 (Supabase 권장)
- Discord Bot Token

### 설치 방법

1. **저장소 클론**
```bash
git clone https://github.com/Pakkoc/studycard-discord-bot.git
cd studycard-discord-bot
```

2. **가상환경 생성 및 활성화**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. **의존성 설치**
```bash
pip install -r requirements.txt
```

4. **환경 변수 설정**
`.env` 파일을 생성하고 다음 내용을 입력:
```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=your_postgresql_connection_string
MAGIC_LIBRARY_CHANNEL_ID=your_channel_id_for_bonus_xp
```

5. **데이터베이스 마이그레이션**
```bash
python scripts/migrate.py
```

6. **봇 실행**
```bash
python src/bot.py
```

## 🎮 명령어

### 사용자 명령어
- `/프로필` - 자신의 학생증 스타일 프로필 카드 표시
- `/스트릭` - 최근 30일간의 활동 달력 표시

### 관리자 명령어
- `/통계` - 서버 전체 활동 통계 (관리자 전용)

## 🏗 프로젝트 구조

```
profile_bot/
├── src/
│   └── bot.py              # 메인 봇 애플리케이션
├── cogs/
│   ├── profile_cog.py      # 프로필 관련 명령어
│   ├── streak_cog.py       # 스트릭 관련 명령어
│   └── slash_basic.py      # 기본 슬래시 명령어
├── core/
│   ├── database.py         # 데이터베이스 연결 및 쿼리
│   ├── imaging.py          # 이미지 생성 (프로필 카드, 달력)
│   └── leveling.py         # 레벨 계산 로직
├── assets/
│   └── db/migrations/      # 데이터베이스 마이그레이션 파일
├── scripts/                # 유틸리티 스크립트
└── vooster-docs/          # 프로젝트 문서
```

## 🎨 기능 세부사항

### 레벨 시스템
| 레벨 | 칭호 | 필요 XP |
|------|------|---------|
| 1 | 견습마법사 | 0 |
| 2 | 초급마법사 | 100 |
| 3 | 중급마법사 | 250 |
| 4 | 고급마법사 | 500 |
| 5 | 전문마법사 | 900 |
| 6 | 마스터 | 1500 |
| 7 | 그랜드마스터 | 2350 |
| 8 | 아크메이지 | 3500 |
| 9 | 엘더 | 5500 |
| 10 | 현자 | 8000 |

### 기숙사 시스템
봇은 사용자의 Discord 역할을 확인하여 자동으로 기숙사를 배정합니다:
- **노블래빗** 🐇: 노블래빗 역할 보유자
- **소용돌이** 🦋: 소용돌이 역할 보유자  
- **볼리베어** 🐻‍❄️: 볼리베어 역할 보유자
- **펭도리아** 🐧: 펭도리아 역할 보유자

역할이 없는 경우 "기숙사를 선택해주세요" 메시지가 표시됩니다.

### 학번 시스템
학번은 사용자가 서버에 처음 참여한 날짜를 기준으로 자동 생성됩니다.
- 형식: YYMMDD (예: 241225)

## 🔧 개발 도구

### 유틸리티 스크립트
- `scripts/migrate.py` - 데이터베이스 마이그레이션 실행
- `scripts/test_db.py` - 데이터베이스 연결 테스트
- `scripts/print_user_stats.py` - 사용자 통계 출력
- `scripts/set_user_xp.py` - 사용자 XP 수동 설정

### 코드 포맷팅
```bash
# 코드 포맷팅
black .
isort .
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여하기

1. 이 저장소를 포크합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📞 지원

문제가 발생하거나 질문이 있으시면 [Issues](https://github.com/Pakkoc/studycard-discord-bot/issues) 페이지에 문의해주세요.

## 📚 추가 문서

자세한 기술 문서는 `vooster-docs/` 폴더를 참조하세요:
- [PRD (제품 요구사항 문서)](vooster-docs/prd.md)
- [아키텍처 문서](vooster-docs/architecture.md)
- [개발 가이드라인](vooster-docs/guideline.md)

---

**Made with ❤️ for the Magic School community**
