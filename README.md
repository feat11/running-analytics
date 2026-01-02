# 🏃‍♂️ @run.seob Running Analytics

Strava 데이터를 기반으로 한 개인 러닝 분석 대시보드

## 🎯 주요 기능

- **실시간 러닝 통계**: 거리, 횟수, 평균 페이스, 최장 거리, 총 고도
- **월간 목표 추적**: 진행률 표시 및 목표 달성 알림
- **연간 활동 히트맵**: GitHub 스타일의 365일 활동 시각화
- **상세 분석**:
  - 월별/주간 거리 트렌드
  - 페이스 개선 추이
  - 페이스 존 분포 (Speed/Tempo/Easy/Recovery)
  - 심박수 분석
- **활동 패턴 분석**: 요일별, 시간대별 러닝 패턴
- **개인 기록**: 최고 페이스, 최장 거리, 연속 기록 (스트릭)
- **자동 업데이트**: 매일 08시 자동으로 Strava 데이터 동기화

## 🚀 설치 및 실행

### 1. 필수 패키지 설치

```bash
pip install streamlit pandas requests plotly numpy
```

### 2. Strava API 설정

1. [Strava API Settings](https://www.strava.com/settings/api)에서 앱 등록
2. `Client ID`, `Client Secret` 발급
3. Refresh Token 발급 (OAuth 플로우 사용)

### 3. Secrets 파일 생성

`.streamlit/secrets.toml` 파일 생성:

```toml
[strava]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
refresh_token = "YOUR_REFRESH_TOKEN"
```

### 4. 로컬 실행

```bash
streamlit run app_improved.py
```

## 🤖 GitHub Actions 자동 업데이트 설정

### 1. Repository Secrets 설정

GitHub 저장소 Settings → Secrets and variables → Actions에서 다음 추가:

- `STRAVA_CLIENT_ID`: Strava Client ID
- `STRAVA_CLIENT_SECRET`: Strava Client Secret
- `STRAVA_REFRESH_TOKEN`: Strava Refresh Token

### 2. 자동 업데이트 동작

- **스케줄**: 매일 UTC 23:00 (한국시간 08:00)
- **수동 실행**: Actions 탭에서 "Run workflow" 클릭
- **동작 방식**: 
  1. Strava API에서 최신 데이터 가져오기 (최대 1000개 활동)
  2. `running_data.csv` 업데이트
  3. `app_config.json` 업데이트
  4. 변경사항 자동 커밋 및 푸시

## 📊 데이터 구조

### running_data.csv
- 모든 러닝 활동 데이터
- 페이스, 거리, 시간, 심박수 등

### app_config.json
```json
{
  "monthly_goal": 100,
  "last_update": "2025-01-02T08:00:00"
}
```

## 🎨 기능 상세

### Key Metrics
- 선택한 기간에 따라 동적으로 변경
- 기본: This Month (이번 달)
- 옵션: All Time, Last 7/30/90 Days, This Year

### 페이스 표시
- 형식: `분:초` (예: 5:30)
- 모든 페이스 관련 지표에 일관되게 적용

### Strava API 제한
- 15분당 100회
- 일일 1,000회
- 자동 업데이트로 제한 최소화

## 📝 파일 구조

```
.
├── app_improved.py          # 메인 Streamlit 앱
├── update_data.py           # GitHub Actions용 업데이트 스크립트
├── running_data.csv         # 러닝 데이터 (자동 생성)
├── app_config.json          # 설정 파일 (자동 생성)
├── .streamlit/
│   └── secrets.toml         # Strava API credentials
├── .github/
│   └── workflows/
│       └── update_strava.yml # GitHub Actions 워크플로우
└── .gitignore
```

## 🔧 커스터마이징

### 월간 목표 변경
- 사이드바 "Monthly Goal"에서 설정
- 자동으로 저장되어 다음 실행 시에도 유지

### 기간 필터
- This Month (기본값)
- All Time
- Last 7/30/90 Days
- This Year

### 차트 커스터마이징
- Plotly 차트 사용
- `app_improved.py`에서 차트 레이아웃 수정 가능

## 🐛 문제 해결

### "KeyError: 'date'" 에러
→ CSV 파일 삭제 후 재시작하면 자동 해결

### 데이터가 200개만 표시됨
→ "Sync Strava Data" 버튼 클릭 (최대 1000개 가져옴)

### API 제한 에러
→ 15분 대기 후 재시도

## 📄 라이선스

MIT License

## 👤 Author

@run.seob
