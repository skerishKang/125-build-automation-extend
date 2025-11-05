# 📂 프로젝트 파일 구조 - 최종 상태

## ✅ 완료된 파일 배치

### 프로젝트 루트 (125-build-automation-extend/)
```
├── .env                              ✅ 환경변수
├── service_account.json              ✅ Drive용 Service Account
├── telegram-google.json              ✅ Gmail+Calendar용 OAuth2 Credentials ⭐
├── token.pickle                      ⏳ (첫 인증 후 자동 생성됨)
├── database.db                       ✅ SQLite 데이터베이스
└── backend/
    ├── bot_runner.py                 ✅ 메인 봇 실행 파일
    └── services/
        ├── gmail.py                  ✅ Gmail 서비스 (경로 수정됨)
        ├── gmail_reply.py            ✅ Gmail 답장 서비스 (경로 수정됨)
        ├── calendar.py               ✅ Calendar 서비스
        ├── drive_sync.py             ✅ Drive 동기화
        └── ... (기타 서비스)
```

## 🔧 수정된 파일들

### 1. backend/services/gmail.py
```python
# 수정 전
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gmail_credentials.json')

# 수정 후 ⭐
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'telegram-google.json')
```

### 2. backend/services/gmail_reply.py
```python
# 수정 전
TOKEN_FILE = os.path.join(tempfile.gettempdir(), 'gmail_reply_token.pickle')
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'gmail_credentials.json')

# 수정 후 ⭐
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'telegram-google.json')
```

## 🎯 파일 접근 경로

### Drive (Service Account)
```
사용하는 파일: service_account.json (프로젝트 루트)
코드에서 접근: '../service_account.json' 또는 절대경로
```

### Gmail + Calendar (OAuth2)
```
사용하는 파일: telegram-google.json (프로젝트 루트)
토큰 파일: token.pickle (첫 인증 후 생성, 프로젝트 루트)
코드에서 접근: '../telegram-google.json' 또는 BASE_DIR 변수
```

## ✅ 인증 설정 완료

### Gmail API 권한
```json
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',      ✅
    'https://www.googleapis.com/auth/gmail.send',          ✅
    'https://www.googleapis.com/auth/calendar'             ✅
]
```

### OAuth2 플로우
1.elegram-google.json (credentials) → 프로젝트 루트에 있음 ✅
2. 첫 인증 시 로컬 서버 실행 (포트 0)
3. 인증 성공 후 token.pickle 자동 생성 (프로젝트 루트)
4. 이후 인증은 token.pickle 사용

## 🚀 다음 단계

1. ✅ 파일 배치 완료
2. ✅ 경로 수정 완료
3. ⏳ Gmail 인증 테스트 실행
4. ⏳ 답장 기능 테스트 실행

## 🧪 인증 테스트 방법

### 방법 1: Gmail Reply 테스트
```bash
cd backend
python -c "from services.gmail_reply import GmailReplyGenerator; g = GmailReplyGenerator(); g.authenticate()"
```

### 방법 2: Gmail 서비스 테스트
```bash
cd backend
python -c "from services.gmail import GmailService; g = GmailService(); g.authenticate()"
```

### 방법 3: 봇 실행
```bash
cd backend
python bot_runner.py
```

## 💡 메모

- 모든 OAuth2 관련 파일은 프로젝트 루트에 통일
- Drive용 Service Account와 Gmail용 OAuth2 분리
- token.pickle은 첫 인증 후에만 생성됨
- credentials 파일은永远 필요

