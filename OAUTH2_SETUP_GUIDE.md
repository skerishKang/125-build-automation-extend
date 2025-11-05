# 🔧 Gmail OAuth2 인증 설정 가이드

## ❌ 현재 문제
```
400 오류: redirect_uri_mismatch
유투브 자동 댓글 챗봇에서 잘못된 요청을 전송했습니다
```

## 🔍 원인 분석
OAuth2 클라이언트에서 redirect URI가 올바르지 않음

## ✅ 해결 방법

### 방법 1: Google Cloud Console에서 수정

1. https://console.cloud.google.com/apis/credentials 접속
2. 사용 중인 OAuth 2.0 Client ID 클릭
3. **승인된 리디렉션 URI** 섹션에서 다음 중 하나 추가:

#### 옵션 A: 데스크톱 앱 (권장)
```
urn:ietf:wg:oauth:2.0:oob
```

#### 옵션 B: 로컬 서버
```
http://localhost:8080/callback
http://127.0.0.1:8080/callback
```

4. **저장** 클릭

### 방법 2: 새 OAuth2 클라이언트 생성 (더 간단)

1. https://console.cloud.google.com/apis/credentials 접속
2. **+ 클라이언트 ID 만들기** 클릭
3. **데스크톱 애플리케이션** 선택
4. 이름: "Telegram Gmail Bot" 입력
5. **만들기** 클릭
6. JSON 다운로드
7. 프로젝트 루트의 telegram-google.json 교체

### 방법 3: 기존 Credentials 수정

googleapis library에서 redirect_uri를 명시적으로 설정:

```python
# gmail_reply.py 수정
def authenticate(self):
    # ...
    flow = InstalledAppFlow.from_client_secrets_file(
        self.credentials_file, 
        SCOPES
    )
    # 명시적으로 redirect URI 설정
    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
    creds = flow.run_local_server(port=0)
    # ...
```

## 🎯 권장 해결 순서

1. **가장 간단한 방법**: 새 OAuth2 클라이언트 생성 (방법 2)
2. **기존 설정 수정**: Google Cloud Console에서 URI 추가 (방법 1)
3. **코드 수정**: redirect_uri 명시적 설정 (방법 3)

## 📱 설정 완료 후

새 telegram-google.json 파일을 프로젝트 루트에 저장:
```
G:\Ddrive\BatangD\task\workdiary\125-build-automation-extend\telegram-google.json
```

## 🧪 테스트

```bash
cd backend
python -c "from services.gmail_reply import GmailReplyGenerator; g = GmailReplyGenerator(); g.authenticate()"
```

## 💡 참고

- **YouTube 자동 댓글 봇**과의 충돌 가능성이 있음
- Google 계정당 여러 OAuth2 앱 가능
- 각각 다른 프로젝트에 설정 필요
- 또는 동일한 프로젝트에서 서로 다른 클라이언트 ID 사용

## ⚠️ 주의사항

한 Google 계정에 여러 OAuth2 앱 연결 시:
1. 각각 고유한 client_id 필요
2. 다른 OAuth2 앱의 credentials 사용하면 충돌
3. 새 클라이언트 ID로 생성해서 사용
