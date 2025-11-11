# Discord Silent Study Tracker Bot 정보 아키텍처 (IA)

## 1. 사이트맵 (사이트맵)

### 웹 대시보드 구조
```
/ (홈/대시보드)
├── /dashboard (메인 대시보드)
├── /members (멤버 관리)
│   ├── /members/:userId (개별 멤버 프로필)
│   └── /members/export (데이터 내보내기)
├── (업적 시스템 – 현재 비활성화)
├── /settings (설정)
│   ├── /settings/general (일반 설정)
│   ├── /settings/achievements (업적 설정)
│   ├── /settings/reports (리포트 설정)
│   └── /settings/premium (프리미엄 관리)
└── /auth (인증)
    ├── /auth/login (로그인)
    └── /auth/callback (Discord OAuth 콜백)
```

### Discord 봇 명령어 구조
```
Discord Bot Commands
├── /profile [@사용자] (프로필 카드 조회)
├── /streak [@사용자] (스트릭 캘린더 조회)
├── (업적 명령어 비활성화)
├── (언어 설정 – 현재 비활성화)
├── /help (도움말)
└── /admin (관리자 전용)
    ├── /admin/report (즉시 리포트 전송)
    └── /admin/settings (봇 설정)
```

## 2. 사용자 흐름 (사용자 흐름)

### 핵심 작업 1: 일반 사용자 - 학습 세션 기록 및 확인
1. 사용자가 "🔇 | Focus Room" 음성 채널에 입장
2. 봇이 자동으로 세션 시작 시간 기록
3. 사용자가 채널에서 나가면 봇이 종료 시간 기록 및 통계 업데이트
4. 레벨업 달성 시 채팅창에 축하 메시지 자동 전송
5. 사용자가 `/profile` 명령어로 개인 통계 확인
6. 프로필 카드 이미지와 함께 오늘/주/월/누적 시간 정보 제공

### 핵심 작업 2: 사용자 - 스트릭 확인
1. 사용자가 `/streak` 명령어로 연속 참여 현황 확인
2. 최근 30일 달력 형태의 스트릭 캘린더 이미지 제공
3. 연속 참여 일수 및 최고 기록 정보 함께 표시

### 핵심 작업 3: 관리자 - 웹 대시보드 활용
1. 관리자가 Discord OAuth로 웹 대시보드 로그인
2. 메인 대시보드에서 서버 전체 통계 한눈에 확인
3. 멤버 관리 페이지에서 개별 사용자 활동 내역 조회
4. 필터 및 검색 기능으로 특정 조건 멤버 찾기
5. CSV 형태로 데이터 내보내기 실행
6. 설정 페이지에서 업적 기준값 및 알림 설정 조정

## 3. 네비게이션 구조 (네비게이션 구조)

### 웹 대시보드 네비게이션
- **고정 사이드바 (280px 너비)**
  - 로고 및 서버명
  - 주요 메뉴 (대시보드, 멤버, 업적, 설정)
  - 사용자 프로필 드롭다운 (로그아웃, 언어 설정)
- **상단 헤더**
  - 페이지 제목
  - 날짜 범위 선택기
  - 알림 아이콘
- **하단 푸터**
  - 버전 정보
  - 지원 링크
  - 개인정보 처리방침

### 모바일 네비게이션
- **하단 탭바** (사이드바 대체)
  - 대시보드, 멤버, 업적, 설정 (4개 탭)
- **햄버거 메뉴** (추가 옵션)
  - 언어 설정, 로그아웃, 도움말

## 4. 페이지 계층 구조 (페이지 계층 구조)

```
/ (Depth 1) - 메인 대시보드
├── /members (Depth 2) - 멤버 목록
│   └── /members/[userId] (Depth 3) - 개별 멤버 상세
├── /achievements (Depth 2) - 업적 시스템
│   ├── /achievements/manage (Depth 3) - 업적 관리
│   └── /achievements/create (Depth 3) - 커스텀 업적 생성
├── /settings (Depth 2) - 설정 메인
│   ├── /settings/general (Depth 3) - 일반 설정
│   ├── /settings/achievements (Depth 3) - 업적 설정
│   ├── /settings/reports (Depth 3) - 리포트 설정
│   └── /settings/premium (Depth 3) - 프리미엄 관리
└── /auth (Depth 2) - 인증
    ├── /auth/login (Depth 3) - 로그인
    └── /auth/callback (Depth 3) - OAuth 콜백
```

## 5. 콘텐츠 구성 (콘텐츠 구성)

| 페이지 | 주요 콘텐츠 요소 |
|---|---|
| 메인 대시보드 | KPI 카드 (오늘/주/월 총 학습시간, 활성 멤버 수), 일별 학습시간 라인 차트, 오늘 TOP 5 멤버 바 차트, 빠른 액션 버튼 |
| 멤버 관리 | 검색/필터 바, 페이지네이션 데이터 테이블 (아바타, 디스코드 태그, 총 시간, 레벨, 스트릭, 업적 수), 프로필 모달 |
| 개별 멤버 상세 | 프로필 카드, 활동 히스토리 캘린더 히트맵, 업적 배지 목록, 통계 차트 |
| 업적 시스템 | 업적 배지 그리드 (아이콘, 이름, 조건, 달성률), 잠금/해제 토글, 관리 도구 |
| 설정 - 일반 | 언어 선택기, 시간대 설정, 서버 기본 설정 폼 |
| 설정 - 업적 | 업적별 기준값 입력 필드, XP 계산 공식 설정, 미리보기 |
| 설정 - 리포트 | 일일/주간 요약 알림 토글, 리포트 템플릿 선택 |
| 로그인 | Discord OAuth 버튼, 서비스 소개, 권한 안내 |

## 6. 인터랙션 패턴 (인터랙션 패턴)

### 주요 인터랙션 패턴
- **모달 다이얼로그**: 개별 멤버 프로필 상세 보기, 설정 확인 팝업
- **툴팁**: 업적 조건 설명, 통계 수치 상세 정보, 도움말 아이콘
- **드롭다운**: 날짜 범위 선택, 필터 옵션, 언어 설정
- **토글 스위치**: 알림 설정, 업적 표시/숨김, 기능 활성화/비활성화
- **페이지네이션**: 멤버 목록, 활동 히스토리 테이블
- **검색 및 필터**: 실시간 검색, 다중 조건 필터링
- **드래그 앤 드롭**: 업적 순서 변경, 대시보드 위젯 배치 (향후)
- **무한 스크롤**: 모바일 멤버 목록, 활동 피드 (향후)

### Discord 봇 인터랙션
- **슬래시 명령어**: 자동완성 지원, 매개변수 힌트 제공
- **임베드 메시지**: 프로필 카드, 에러 메시지
- **이미지 생성**: Pillow 기반 동적 카드/캘린더 이미지
- **DM 알림**: 레벨업, 업적 달성, 스트릭 경고 개인 메시지

## 7. URL 구조 (URL 구조)

### 웹 대시보드 URL 규칙
- **루트**: `/` (메인 대시보드)
- **리소스 목록**: `/resource-name` (예: `/members`, `/achievements`)
- **리소스 상세**: `/resource-name/:id` (예: `/members/123456789`)
- **리소스 액션**: `/resource-name/action` (예: `/members/export`)
- **설정 하위**: `/settings/category` (예: `/settings/general`)
- **인증 관련**: `/auth/action` (예: `/auth/login`, `/auth/callback`)

### SEO 친화적 URL 예시
```
/ (메인 대시보드)
/members (멤버 목록)
/members/123456789 (특정 멤버)
/members/export (데이터 내보내기)
/achievements (업적 시스템)
/achievements/manage (업적 관리)
/settings/general (일반 설정)
/auth/login (로그인)
```

## 8. 컴포넌트 계층 구조 (컴포넌트 계층 구조)

### 글로벌 컴포넌트
- **Layout**: 전체 페이지 레이아웃 래퍼
- **Sidebar**: 고정 사이드바 네비게이션
- **Header**: 상단 헤더 (제목, 날짜 선택기, 알림)
- **Footer**: 하단 푸터 (버전, 링크)
- **LoadingSpinner**: 로딩 상태 표시
- **ErrorBoundary**: 에러 처리 및 표시
- **Modal**: 범용 모달 다이얼로그
- **Toast**: 알림 메시지 (성공/에러/경고)

### 페이지별 컴포넌트
#### 대시보드 컴포넌트
- **KPICard**: 핵심 지표 카드 (총 시간, 활성 멤버 등)
- **StudyTimeChart**: 일별 학습시간 라인 차트
- **TopMembersChart**: 상위 멤버 바 차트
- **QuickActions**: 빠른 액션 버튼 패널

#### 멤버 관리 컴포넌트
- **MemberTable**: 페이지네이션 멤버 테이블
- **MemberRow**: 개별 멤버 행 (아바타, 통계, 액션)
- **MemberProfile**: 멤버 상세 프로필 모달
- **FilterBar**: 검색 및 필터 바
- **ExportButton**: CSV 내보내기 버튼

#### 업적 시스템 컴포넌트
- **AchievementGrid**: 업적 배지 그리드 레이아웃
- **AchievementBadge**: 개별 업적 배지 (아이콘, 이름, 진행률)
- **AchievementModal**: 업적 상세 정보 모달
- **ProgressBar**: 업적 달성 진행률 바

#### 설정 컴포넌트
- **SettingsForm**: 범용 설정 폼
- **LanguageSelector**: 언어 선택 드롭다운
- **ToggleSwitch**: 토글 스위치 (알림 설정 등)
- **ThresholdInput**: 수치 입력 필드 (업적 기준값)

#### 공통 UI 컴포넌트
- **Button**: 기본/보조/성공/경고 버튼
- **Card**: 콘텐츠 카드 (둥근 모서리, 그림자)
- **Avatar**: 사용자 아바타 이미지
- **Badge**: 레벨/상태 배지
- **Tooltip**: 도움말 툴팁
- **DatePicker**: 날짜 범위 선택기
- **SearchInput**: 검색 입력 필드
- **Pagination**: 페이지네이션 네비게이션

### 모바일 전용 컴포넌트
- **BottomTabBar**: 하단 탭바 네비게이션
- **SwipeableCard**: 스와이프 가능한 카드
- **PullToRefresh**: 당겨서 새로고침
- **FloatingActionButton**: 플로팅 액션 버튼

### Discord 봇 이미지 생성 컴포넌트 (Pillow 기반)
- **ProfileCardRenderer**: 프로필 카드 이미지 생성
- **StreakCalendarRenderer**: 스트릭 캘린더 이미지 생성
- (AchievementRenderer – 비활성화)
- **LevelUpRenderer**: 레벨업 축하 이미지 생성