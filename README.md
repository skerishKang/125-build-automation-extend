# 125 Build Automation Extend 🚀

**SaaS형 AI 허브 확장 버전** - Google OAuth 기반 다중 사용자 플랫폼

기존 124-build-automation(개인형 AI 자동화 봇)을 여러 사용자가 동시에 사용할 수 있는 SaaS형 서비스로 확장한 프로젝트입니다.

## ✨ 주요 기능

- 🔐 **Google OAuth2 로그인** - 보안되고 빠른 인증
- 🔑 **API 키 관리** - Telegram, Slack, Gmail, Drive, Notion, n8n, Gemini 등
- 🔒 **AES256 암호화** - API 키를 안전하게 저장
- ✅ **실시간 검증** - API 키 유효성 실시간 확인
- 📊 **대시보드** - 직관적인 관리 인터페이스
- 🎨 **Tailwind CSS** - 반응형 디자인

## 🏗️ 기술 스택

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **SQLAlchemy** - ORM (SQLite/PostgreSQL 지원)
- **authlib** - Google OAuth2 인증
- **cryptography** - AES256 암호화
- **uvicorn** - ASGI 서버

### Frontend
- **Next.js 14** - React 기반 풀스택 프레임워크
- **TypeScript** - 타입 안전성
- **Tailwind CSS** - 스타일링
- **SWR** - 데이터 페칭

## 📁 프로젝트 구조

```
125-build-automation-extend/
├── backend/                    # FastAPI 백엔드
│   ├── main.py                # 메인 서버 파일
│   ├── routers/               # API 라우터
│   │   ├── auth.py           # Google OAuth 라우터
│   │   └── verify_keys.py    # API 키 검증 라우터
│   ├── services/             # 외부 API 서비스
│   │   ├── telegram.py       # Telegram API
│   │   └── slack.py          # Slack API
│   ├── utils/                # 유틸리티
│   │   └── crypto.py         # AES 암호화/복호화
│   ├── models/               # 데이터베이스 모델
│   │   └── user.py           # User, Credential 모델
│   └── requirements.txt      # Python 의존성
│
├── frontend/                  # Next.js 프론트엔드
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── index.tsx        # 로그인 페이지
│   │   ├── dashboard.tsx    # 대시보드 페이지
│   │   └── _app.tsx         # 앱 기본 설정
│   ├── components/          # 재사용 컴포넌트
│   │   ├── ServiceCard.tsx  # 서비스 카드
│   │   └── Toast.tsx        # 알림 토스트
│   └── styles/              # 스타일시트
│       └── globals.css      # 전역 스타일
│
└── README.md                 # 이 파일
```

## 🚀 빠른 시작

### 사전 요구사항
- Node.js >= 18.0.0
- Python >= 3.9
- Google OAuth2 애플리케이션 (클라이언트 ID, 시크릿)

### 1. Google OAuth 설정

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "APIs & Services" > "OAuth consent screen" 설정
4. "Credentials" > "Create Credentials" > "OAuth 2.0 Client IDs"
5. authorized redirect URI 추가: `http://localhost:8000/auth/callback`
6. 클라이언트 ID와 시크릿 복사

### 2. 백엔드 설정

```bash
# 백엔드 디렉토리로 이동
cd backend

# Python 패키지 설치
pip install -r requirements.txt

# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (Nano/Vim 사용)
nano .env
```

`.env` 파일 내용:
```env
SECRET_KEY=your-super-secret-key-change-this
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
JWT_SECRET=your-jwt-secret-key
DATABASE_URL=sqlite:///./database.db
AES_KEY=your-32-byte-encryption-key-here
FRONTEND_URL=http://localhost:3000
```

**AES 키 생성** (Python에서):
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 3. 프론트엔드 설정

```bash
# 새 터미널에서 프론트엔드 디렉토리로 이동
cd frontend

# npm 패키지 설치
npm install

# 환경변수 설정 (.env.local 파일 생성)
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
```

### 4. 서버 실행

#### 백엔드 서버 (터미널 1)
```bash
# 프로젝트 루트에서 실행 (중요)
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
➡️ http://localhost:8000/docs (API 문서 확인 가능)

#### 프론트엔드 서버 (터미널 2)
```bash
cd frontend
npm run dev
```
➡️ http://localhost:3000

### 5. 접속 및 테스트

1. 브라우저에서 http://localhost:3000 접속
2. "Google로 시작하기" 버튼 클릭
3. Google 계정으로 로그인
4. 대시보드에서 API 키 등록 및 검증

## 🔑 API 키 발급 가이드

### Telegram
1. Telegram에서 [@BotFather](https://t.me/BotFather) 검색
2. `/newbot` 명령어 전송
3. 봇 이름과 사용자명 입력
4. 받은 Bot Token을 복사

**예시**: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### Slack
1. [api.slack.com/apps](https://api.slack.com/apps) 접속
2. "Create New App" 클릭
3. "From scratch" 선택
4. 앱 이름과 워크스페이스 선택
5. "OAuth & Permissions" > "Bot Token Scopes" 설정
6. "Install to Workspace" 클릭
7. "Bot User OAuth Token" 복사

**예시**: `xoxb-your-bot-token-here`

## 📚 API 엔드포인트

### 인증 관련
- `GET /auth/login` - Google 로그인 페이지로 리다이렉트
- `GET /auth/callback` - Google OAuth 콜백 처리
- `GET /auth/me` - 현재 사용자 정보 조회
- `POST /auth/logout` - 로그아웃

### API 키 검증
- `POST /verify/{service_name}` - API 키 검증
- `GET /verify/status` - 검증된 키 목록 조회
- `DELETE /verify/{service_name}` - API 키 삭제

### 기타
- `GET /health` - 서버 상태 확인
- `GET /docs` - Swagger API 문서

## 🔒 보안 정보

- API 키는 **AES256 암호화**로 저장됩니다
- 세션 기반 인증을 사용합니다
- CORS 설정을 통해 허용된 도메인만 접근 가능합니다
- 환경변수로 비밀 키를 관리합니다

## 📦 데이터베이스

### 기본 SQLite
- 파일 기반 데이터베이스로 로컬 개발에 적합
- 설정: `DATABASE_URL=sqlite:///./database.db`

### 프로덕션 PostgreSQL (향후)
- 확장성과 성능을 위해 PostgreSQL 사용 권장
- 설정 예시: `DATABASE_URL=postgresql://user:pass@localhost/dbname`

## 🛠️ 개발 가이드

### 새 서비스 추가하기

1. `backend/services/`에 `{service}.py` 파일 생성
2. `{service}_token()` 검증 함수 구현
3. `backend/routers/verify_keys.py`에 라우터 추가
4. `frontend/pages/dashboard.tsx`에 서비스 카드 추가
5. `frontend/components/ServiceCard.tsx`에 서비스 아이콘 추가

### 예시: Gmail API 추가

```python
# backend/services/gmail.py
def verify_gmail_token(token: str) -> dict:
    # Gmail API 검증 로직
    pass
```

```python
# backend/routers/verify_keys.py (추가)
elif service_name == 'gmail':
    return gmail.verify_gmail_token(api_key)
```

## 🚢 배포

### Vercel (프론트엔드)
1. Vercel 계정 생성
2. GitHub 레포지토리 연결
3. `NEXT_PUBLIC_API_BASE` 환경변수 설정
4. 자동 배포

### Render/Fly.io (백엔드)
1. 레포지토리를 GitHub에 푸시
2. Render/Fly.io에서 새 Web Service 생성
3. Python environment 선택
4. Build Command: `pip install -r backend/requirements.txt`
5. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

## ❓ 문제 해결

### CORS 오류
- 백엔드의 `FRONTEND_URL` 환경변수 확인
- 프론트엔드 `NEXT_PUBLIC_API_BASE` 확인

### OAuth 리다이렉트 오류
- Google Cloud Console에서 authorized redirect URI 확인
- 포트 번호와 경로 정확히 입력

### API 키 검증 실패
- API 키가 유효한지 확인
- 네트워크 연결 상태 확인
- 백엔드 로그에서 오류 메시지 확인

## 📝 라이선스

MIT License

## 🤝 기여하기

프로젝트 개선을 위한Pull Request와 Issue를 환영합니다!

---

**Made with ❤️ for 125 Build Automation Project**
