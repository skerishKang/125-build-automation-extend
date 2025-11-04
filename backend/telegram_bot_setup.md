# Telegram Bot Token 설정 방법

## 1. Bot 토큰 발급받기
1. Telegram에서 @BotFather에게 "/newbot" 전송
2. Bot 이름 입력 (예: "MyBot")
3. 사용자명 입력 (예: "my_bot")
4. 토큰 확인
5. 예시 토큰: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

## 2. 환경변수 설정
backend/.env 파일에서:
```
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

## 3. 확인하기
python backend/bot_runner.py 실행 후 로그에서 확인

## 주의사항
- 토큰은 절대 공개하지 마세요!
- 토큰이 유출되면 악용될 수 있습니다
