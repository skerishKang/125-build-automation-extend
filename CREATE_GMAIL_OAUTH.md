# Gmail용 OAuth 클라이언트 생성 가이드

## 🚨 문제: YouTube API용 OAuth 클라이언트를 Gmail에 사용하려고 함

현재 클라이언트: `668455130296-p8idcmd5lgc39r1hur3anhcg6o0081e2.apps.googleusercontent.com`
이름: "telegram-google" (YouTube API용)

## ✅ 해결 방법: Gmail용 새 OAuth 클라이언트 생성

### 단계 1: Gmail API 활성화
1. Google Cloud Console → https://console.cloud.google.com/apis/library/gmail.googleapis.com
2. **"활성화"** 클릭

### 단계 2: OAuth 동의 화면 구성
1. https://console.cloud.google.com/apis/credentials/consent
2. **External** 선택 → **"CREARE"**
3. **User information** 입력:
   - App name: `Gmail Bot`
   - User support email: 사용자 이메일
   - Developer contact: 사용자 이메일
4. **Scopes** → **"ADD OR REMOVE SCOPES"**:
   - `https://www.googleapis.com/auth/gmail.modify` 검색 → 추가
   - `https://www.googleapis.com/auth/gmail.readonly` 검색 → 추가
5. **Save and Continue** → **Publish App**

### 단계 3: OAuth 2.0 클라이언트 생성
1. https://console.cloud.google.com/apis/credentials
2. **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. **Application type**: Desktop application
4. **Name**: `gmail-desktop-client`
5. **Create**
6. **Download JSON** → `gmail_client_credentials.json`

### 단계 4: 파일 교체
```bash
# 다운로드한 파일을 백엔드로 복사
cp gmail_client_credentials.json backend/gmail_credentials.json

# 또는 백업 후 교체
mv backend/gmail_credentials.json backend/gmail_credentials_old.json
cp gmail_client_credentials.json backend/gmail_credentials.json
```

### 단계 5: 인증 재시도
```bash
.venv/bin/python manual_gmail_auth.py
```

## 🔍 확인 방법

성공 시:
- 브라우저에서 Gmail 로그인
- "Google hasn't verified this app" 경고 → **"Advanced"** → **"Go to gmail-desktop-client (unsafe)"**
- **"Allow"** 클릭
- 터미널에 "SUCCESS! Gmail OAuth2 Authentication Completed" 메시지

## ⚠️ 중요

- Gmail API를 활성화해야 합니다
- 스코프에 `gmail.modify`가 포함되어야 합니다
- 앱 유형을 "Desktop application"으로 선택해야 합니다 (Gmail Bot은 웹 앱 아님)
