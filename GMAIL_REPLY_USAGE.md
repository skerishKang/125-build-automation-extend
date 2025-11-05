# 📧 Gmail AI 답장 시스템 사용 가이드

## 🎯 기능 개요
- AI 기반 자동 답장 생성 (Gemini 2.0 Flash)
- 다양한 톤 지원 (professinal, friendly, concise, detailed)
- 실시간 편집 및 전송
- 자연어 명령어 지원

## 🚀 사용법

### 1. 기본 명령어

#### Gmail 최근 메일 목록 보기
```bash
/gmail_list
```
- 읽지 않은 메일 20개까지 표시
- 메일 ID 포함

#### Gmail 답장 생성
```bash
/gmail_reply <메일ID>
```
예시:
```
/gmail_reply 1a2b3c4d5e6f
```

#### 빠른 메일 선택
```bash
/gmail_recent
```
- 최근 메일 5개 목록
- 메일 ID 바로 복사 가능

### 2. 자연어 사용 (하이브리드 모드)

#### 간단한 요청
```
"메일 확인해줘" → /gmail_list 실행
"답장 써줘" → /gmail_reply 실행 (최근 메일)
"김부장님 메일 답장" → 최근 김부장님 메일에 답장
```

### 3. 답장 생성 과정

1. **메일 조회**: 지정된 메일의 내용, 발신자, 제목 추출
2. **AI 분석**: Gemini가 메일 내용 분석
3. **초안 생성**: 상황에 맞는 답장 초안 작성
4. **사용자 선택**:
   - 📤 바로 보내기
   - ✏️ 수정하기
   - 🔄 다른 톤으로
   - ❌ 취소

### 4. 톤 종류

#### Professional (기본)
```
안녕하세요,
이메일 주셔서 감사합니다.
문의하신 사항에 대해 검토 후 회신드리겠습니다.
감사합니다.
```

#### Friendly
```
안녕하세요!
메일 확인했습니다. 😊
담당자와 상의해서 빠르게 답해드리겠습니다!
감사합니다!
```

#### Concise
```
안녕하세요.
메일 확인했습니다. 조만간 회신드리겠습니다.
감사합니다.
```

### 5. 편집 기능

#### 수정하기 버튼 클릭 후
```
✏️ 수정하실 내용을 다음 메시지로 보내주세요.
```
- 새 답장 내용 입력
- 기존 답장 대신 사용

#### 다른 톤으로 재생성
- professional → friendly → concise 순서로 순환
- 매번 새로운 초안 생성

## 🔧 설정 요구사항

### Gmail API 권한
1. Gmail API 활성화
2. OAuth 2.0 클라이언트 생성
3. 권한 추가:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send` ⭐ (중요!)
4. `gmail_credentials.json` 다운로드
5. `backend/services/` 폴더에 저장

### Gemini API
- `GEMINI_API_KEY` 환경변수 설정
- 없으면 템플릿 기반 답장 사용

## 📱 전체 명령어

| 명령어 | 설명 |
|--------|------|
| `/gmail_list` | 메일 목록 보기 |
| `/gmail_on` | Gmail 감시 시작 |
| `/gmail_off` | Gmail 감시 중지 |
| `/gmail_status` | Gmail 상태 확인 |
| `/gmail_reply <ID>` | AI 답장 생성 |
| `/gmail_recent` | 최근 메일 목록 |

## 🎮 고급 사용법

### Multi-turn 대화
```
사용자: "메일 확인"
봇: "📧 Gmail 메일 5개를 확인했어요!"

사용자: "첫 번째꺼 답장 써줘"
봇: "✏️ 김부장님께 답장을 작성해드릴게요..."
     [초안 표시]
     [보내기] [수정] [다른톤] [취소]
```

### 작업 흐름
1. `/gmail_list`로 메일 확인
2. 메일 ID 복사
3. `/gmail_reply <메일ID>` 실행
4. AI 초안 확인
5. 필요시 수정/다른 톤
6. 전송!

## 🐛 문제 해결

### 인증 실패
```
❌ Gmail 인증 실패
```
해결: `gmail_credentials.json` 파일 확인

### 답장 전송 실패
```
❌ 답장 전송에 실패했습니다
```
해결: Gmail API에 `gmail.send` 권한 추가 확인

### 파일 위치
- 인증 파일: `backend/services/gmail_credentials.json`
- 토큰 파일: `~/.tmp/gmail_reply_token.pickle`

## 💡 팁

1. **빠른 접근**: `/gmail_recent`로 메일 ID 바로 확인
2. **자연어**: "답장 써줘"로 간단하게 사용
3. **편집**: 수정 후 바로 전송 가능
4. **톤 변경**: 여러 톤으로試해보기
5. **스레드**: 답장 시 자동으로 스레드에 추가

## 🎯 실용 예시

### 비즈니스 메일
```
收到: "프로젝트 진행 상황 보고 요청"
AI 초안: "안녕하세요, 프로젝트 진행 관련 문의 주셔서 감사합니다. 
         현재 진행 상황은... [상세 내용]"
```

### 개인정보 메일
```
收到: "점심 약속 확인"
AI 초안: "안녕하세요! 😊 네, 내일 점심 약속 확인했습니다. 
         12시쯤 만날까요?"
```

## 🚀 바로 시작하기

1. Gmail API 설정 완료 ✅
2. 봇 실행: `python backend/bot_runner.py` ✅
3. `/gmail_recent` 실행 ✅
4. `/gmail_reply <메일ID>` 실행 ✅
5. 답장 전송! ✅

**메일 처리 속도 10배 향상!** 🚀
