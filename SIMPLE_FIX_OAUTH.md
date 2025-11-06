# Gmail OAuth 간단한 해결법

## 🚨 문제
기존 클라이언트 "telegram-google"는 Gmail 스코프가 없어서 오류 발생

## ✅ 간단한 해결법 (이름 변경 NO!)

### 1. OAuth 동의 화면에 Gmail 스코프만 추가하면 됩니다!

**이름 변경은 의미없음** - 중요한 건 스코프입니다!

### 2. 단계 (이미 동의 화면 구성했다면):

**TB: OAuth 동의 화면** 페이지로 이동:
```
https://console.cloud.google.com/apis/credentials/consent
```

**"SCOPES" 섹션 클릭**

**"추가 또는 제거" 버튼 클릭**

**검색:**
```
gmail
```

**추가할 항목:**
- ☑️ Gmail API - gmail.modify (읽기,쓰기)
- ☑️ Gmail API - gmail.readonly (읽기 전용)

**"저장"**

### 3. 테스트
```bash
.venv/bin/python manual_gmail_auth.py
```

**브라우저 경고:** "Google hasn't verified this app" → "고급" → "계속 진행" 클릭

## ⚠️ 중요

이름 변경이 아니라 **스코프 추가**가 중요합니다!

- 클라이언트 ID: 668455130296-p8idcmd5lgc39r1hur3anhcg6o0081e2.apps.googleusercontent.com (변경 无)
- 중요한 건: Gmail 스코프가 있는지 (있으면 정상 작동)
