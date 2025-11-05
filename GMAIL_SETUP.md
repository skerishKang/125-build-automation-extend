# 📧 Gmail Integration Setup Guide

## 🎯 Overview
Gmail integration has been added to your Telegram bot with the following features:
- Real-time email monitoring (5-minute intervals)
- AI-powered email summarization using Gemini 2.5 Flash
- Unread email tracking
- Background processing

## 📋 New Commands

### Core Gmail Commands
```
/gmail_on      → Start Gmail monitoring 📧
/gmail_off     → Stop Gmail monitoring 📪
/gmail_status  → Check monitoring status 📊
/gmail_list    → List recent emails 📋
```

## 🔧 Setup Instructions

### Step 1: Enable Gmail API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Choose "Desktop application"
4. Download the JSON file
5. **Rename it to**: `gmail_credentials.json`
6. **Place it in**: `backend/gmail_credentials.json`

### Step 3: First Authentication
1. Start the bot: `python backend/bot_runner.py`
2. Send `/gmail_on` to your bot
3. Your default browser will open for Gmail authorization
4. Grant permissions
5. The token will be saved automatically for future use

## 📊 Usage Examples

### Start Monitoring
```
User: /gmail_on
Bot: 📧 Gmail 연결 테스트 중...
Bot: ✅ Gmail 연결 성공! 감시를 시작합니다...
Bot: 🟢 Gmail 실시간 감시 시작!
```

### Check Status
```
User: /gmail_status
Bot: 📊 Gmail 감시 상태

🟢 상태: 실행 중
🕒 마지막 확인: 14:25:33
📧 처리된 메일: 3개
🔵 현재 받은편지함: 7개
```

### List Emails
```
User: /gmail_list
Bot: 📧 최근 메일 목록 가져오는 중...
Bot: 📋 최근 Gmail 목록 (최대 10개)

1. 🔵 **긴급: 프로젝트 승인 요청**
   👤 김철수 <kim@company.com>
   🕒 2025-11-05 14:15
...
```

### Stop Monitoring
```
User: /gmail_off
Bot: 📪 Gmail 감시 중지됨

📊 이번 세션 통계:
- 처리된 메일: 5개
- 감시 시간: 2025-11-05T14:15:00부터
```

## ⚙️ How It Works

### Monitoring Loop
- Checks every 5 minutes for new unread emails
- Processes only unread emails (marked as UNREAD)
- AI summarization using Gemini 2.5 Flash
- Tracks processed emails to avoid duplicates

### Email Processing
1. **Detection**: Finds new unread emails
2. **Extraction**: Retrieves email content (subject, sender, body)
3. **AI Analysis**: Gemini summarizes:
   - Key points (2-3 sentences)
   - Priority level (High/Medium/Low)
   - Required actions if any
4. **Notification**: Sends summary to Telegram

## 🔒 Security Features
- OAuth2 authentication (not stored passwords)
- Token-based authentication (refreshable)
- Local token storage (`gmail_token.pickle`)
- Processed email tracking (`gmail_processed.json`)
- Read-only API scope (cannot send emails)

## 📁 Files Created/Modified

### New Files
- `backend/services/gmail.py` - Gmail API service class
- `GMAIL_SETUP.md` - This guide

### Modified Files
- `backend/bot_runner.py` - Added Gmail handlers and monitoring

## 🚨 Troubleshooting

### "Gmail credentials file not found"
- **Solution**: Follow Step 2 above to create and place `gmail_credentials.json`

### "Gmail authentication failed"
- **Solution**: Delete `gmail_token.pickle` and run `/gmail_on` again

### "No new emails found"
- **Solution**: Check if you have unread emails in Gmail
- Unread emails are determined by Gmail's UNREAD label

### "Email processing error"
- **Solution**: Check if GEMINI_API_KEY is set (required for AI summarization)

## 🎯 Next Steps

1. ✅ Set up Gmail API credentials
2. ✅ Run `/gmail_on` to start monitoring
3. ✅ Test with `/gmail_list` to see recent emails
4. ✅ Wait for new emails to be automatically processed

## 💡 Pro Tips

### Custom Email Filtering
Edit `backend/services/gmail.py` line 45 to change email query:
```python
q='is:unread'  # Change this for different filters
```
Examples:
- `is:unread from:boss@company.com` - Unread from specific sender
- `is:unread subject:urgent` - Unread with "urgent" in subject
- `is:unread newer_than:7d` - Unread from last 7 days

### Adjusting Check Interval
The default is 5 minutes (300 seconds). To change:
Edit `bot_runner.py` line 1020:
```python
for _ in range(300):  # Change 300 to your desired seconds
```

## 📞 Support
If you encounter issues:
1. Check logs in `logs/bot_runner.log`
2. Verify credentials file location
3. Ensure Gmail API is enabled
4. Check internet connection

---

**Enjoy your new Gmail integration! 📧✨**
