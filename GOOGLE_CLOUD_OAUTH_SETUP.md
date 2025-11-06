# Google Cloud OAuth2 리다이렉트 URI 설정

## 🚨 오류 해결: redirect_uri_mismatch

OAuth2 인증 시 "redirect_uri_mismatch" 오류가 발생하는 경우 해결 방법입니다.

## ✅ 해결 방법

### 1. Google Cloud Console 접속
```
https://console.cloud.google.com/apis/credentials
```

### 2. OAuth 2.0 클라이언트 찾기
**클라이언트 ID**: `668455130296-p8idcmd5lgc39r1hur3anhcg6o0081e2.apps.googleusercontent.com`

### 3. 리다이렉트 URI 추가
**autorization redirect URI** 섹션에 다음 URI 추가:

#### 필수 URI:
```
http://localhost:8080
```

#### 추가 권장 URI (경우에 따라):
```
http://127.0.0.1:8080
```

### 4. 저장
변경 사항을 저장하고 **봇을 재시작**한 후 Gmail 인증을 다시 시도합니다.

## 🔍 확인 방법

변경 후 다음 명령어로 테스트:
```bash
.venv/bin/python manual_gmail_auth.py
```

성공하면 브라우저에서 Gmail 로그인 → 권한 허용 → 인증 완료 메시지

## ⚠️ 포트 충돌 시

다른 포트를 사용하고 싶다면:
1. `backend/services/gmail.py:120`을 수정
2. `port=8080`을 원하는 포트로 변경
3. Google Cloud Console에 해당 포트를 추가
