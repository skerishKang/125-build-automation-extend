# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

### Running the Application

**Backend (FastAPI):**
```bash
# From project root
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

**Frontend (Next.js):**
```bash
cd frontend
npm install
npm run dev
```
- App URL: http://localhost:3000

**Using Batch Scripts:**
- Windows: Double-click `start-backend.bat` or `start-frontend.bat`
- Or run from project root: `start-backend.bat` and `start-frontend.bat`

### Environment Setup

**Backend (.env at backend/.env):**
```env
SECRET_KEY=your_fastapi_secret_here_change_in_production
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET=your_jwt_secret_here_change_in_production
DATABASE_URL=sqlite:///./database.db
AES_KEY=your_32_byte_encryption_key_here_change_in_production
FRONTEND_URL=http://localhost:3000
```

**Generate AES Key:**
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

**Frontend (.env.local at frontend/.env.local):**
```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Architecture Overview

### Tech Stack

**Backend:**
- FastAPI - High-performance Python web framework
- SQLAlchemy - ORM (SQLite/PostgreSQL support)
- Authlib - Google OAuth2 authentication
- Cryptography - AES256 encryption for API keys
- Uvicorn - ASGI server

**Frontend:**
- Next.js 14 - Full-stack React framework
- TypeScript - Type safety
- Tailwind CSS - Styling
- SWR - Data fetching

### Project Structure

```
125-build-automation-extend/
├── backend/                      # FastAPI backend
│   ├── main.py                  # Main server, CORS config, router registration
│   ├── routers/                 # API route handlers
│   │   ├── verify_keys.py       # API key verification endpoints
│   │   └── auth.py              # Google OAuth routes (future)
│   ├── services/                # External API integrations
│   │   ├── telegram.py          # Telegram Bot API validation
│   │   ├── slack.py             # Slack API validation
│   │   └── __init__.py
│   ├── models/                  # Database models
│   │   └── user.py              # User & Credential models
│   ├── utils/                   # Utilities
│   │   └── crypto.py            # AES encryption/decryption
│   └── requirements.txt         # Python dependencies
│
├── frontend/                    # Next.js frontend
│   ├── pages/                   # Page components
│   │   ├── index.tsx            # Redirects to /dashboard
│   │   ├── dashboard.tsx        # Main dashboard with API key verification
│   │   └── _app.tsx             # App wrapper
│   ├── components/              # Reusable components
│   │   ├── ServiceCard.tsx      # Service verification card
│   │   └── Toast.tsx            # Notification component
│   └── styles/                  # Global styles
│       └── globals.css
│
├── database.db                  # SQLite database
├── start-backend.bat           # Windows backend startup script
└── start-frontend.bat          # Windows frontend startup script
```

## Key Components

### Backend Flow

**Main Server (backend/main.py):**
- FastAPI app initialization with CORS middleware
- Routes requests to `/verify/*` endpoint via verify_keys router
- Database initialization on startup
- CORS allows localhost:3000, :3001, :3002 and FRONTEND_URL env var

**API Key Verification (backend/routers/verify_keys.py):**
- `POST /verify/{service_name}` - Validates API keys
- Current implementation: **No authentication** (simple validation version)
- Supported services: `telegram`, `slack`
- Returns validation status without storing keys

**Service Validators:**
- `backend/services/telegram.py` - Calls `https://api.telegram.org/bot{token}/getMe`
- `backend/services/slack.py` - Validates Slack Bot tokens
- Both return `{'valid': bool, 'error' or 'bot_info': dict}`

**Database Models (backend/models/user.py):**
- `User` - Google OAuth user data (email, name, google_id, picture)
- `Credential` - Encrypted API keys per user (future feature)
- SQLite database with SQLAlchemy ORM
- `init_db()` - Creates all tables

### Frontend Flow

**Dashboard (frontend/pages/dashboard.tsx):**
- Fetches API base from `NEXT_PUBLIC_API_BASE` env var
- Manages verification state with `verifiedServices` state
- Shows service cards for Telegram and Slack
- Displays toast notifications for success/error

**Service Card (frontend/components/ServiceCard.tsx):**
- Input field for API key
- Verify button that calls `POST /verify/{service_name}`
- Visual feedback (success/error states)

## Adding New Services

**Step 1: Create Validator Service**
```python
# backend/services/{service_name}.py
import requests

def verify_{service_name}_token(token: str) -> dict:
    """
    Validate {service_name} API token
    Returns: {'valid': bool, 'error' or 'api_info': dict}
    """
    # API validation logic here
    try:
        # Example API call
        # response = requests.get(f'https://api.{service_name}.com/token/validate?token={token}')
        # data = response.json()
        # return {'valid': True, 'api_info': data}
        pass
    except Exception as e:
        return {'valid': False, 'error': str(e)}
```

**Step 2: Register Validator**
```python
# backend/routers/verify_keys.py
async def _verify_service_key(service_name: str, api_key: str) -> dict:
    from backend.services import telegram, slack, {service_name}

    if service_name == 'telegram':
        return telegram.verify_telegram_token(api_key)
    elif service_name == 'slack':
        return slack.verify_slack_token(api_key)
    elif service_name == '{service_name}':
        return {service_name}.verify_{service_name}_token(api_key)
    else:
        return {'valid': False, 'error': f'Service {service_name} not supported'}
```

**Step 3: Add Frontend Service Card**
```tsx
// frontend/pages/dashboard.tsx
const services = [
  // ...existing services
  {
    name: '{service_name}',
    title: '{Service Name}',
    description: '{service_name} API Token',
    placeholder: 'your-{service_name}-token-here',
    icon: <YourIcon />
  }
]
```

## API Endpoints

### Verification
- `POST /verify/{service_name}` - Validate API key
  - Body: `{"api_key": "string"}`
  - Returns: `{"status": "success", "service": "...", "verified": true, "valid": true, "message": "..."}`

### System
- `GET /health` - Server health check
- `GET /` - API information
- `GET /config` - Environment configuration status

## Development Notes

### Database
- SQLite by default (`DATABASE_URL=sqlite:///./database.db`)
- Switch to PostgreSQL for production:
  ```env
  DATABASE_URL=postgresql://user:pass@localhost/dbname
  ```

### CORS Configuration
- Backend allows localhost:3000, :3001, :3002 by default
- Custom URL via `FRONTEND_URL` environment variable
- Update in `backend/main.py:31-39`

### Encryption
- AES256 for API key storage (future feature)
- Use `backend/utils/crypto.py` for encrypt/decrypt
- Generate key: `Fernet.generate_key()`

### Current Limitations (v0.2.0)
- **No authentication** - Simple verification only
- **No persistence** - Keys not stored after verification
- **Limited services** - Only Telegram and Slack supported
- **SQLite only** - No production database setup

### OAuth Setup (Future Enhancement)
1. Create Google Cloud Console project
2. Enable Google+ API
3. Configure OAuth consent screen
4. Add authorized redirect URI: `http://localhost:8000/auth/callback`
5. Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`

## Testing Services

**Telegram Bot:**
1. Message @BotFather on Telegram
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy Bot Token (format: `123456789:ABC-DEF...`)
5. Paste into Telegram service card

**Slack Bot:**
1. Visit https://api.slack.com/apps
2. Create new app
3. Add Bot Token Scopes
4. Install to workspace
5. Copy "Bot User OAuth Token" (starts with `xoxb-`)

## Deployment

**Backend (Render/Fly.io):**
1. Build Command: `pip install -r backend/requirements.txt`
2. Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables in platform dashboard

**Frontend (Vercel):**
1. Connect GitHub repository
2. Set `NEXT_PUBLIC_API_BASE` environment variable
3. Auto-deploy on git push

## Troubleshooting

**Import Errors:**
- Always run `uvicorn` from **project root** (not backend folder)
- This ensures `backend.*` imports resolve correctly

**CORS Errors:**
- Check `FRONTEND_URL` in backend `.env`
- Verify `NEXT_PUBLIC_API_BASE` in frontend `.env.local`
- Confirm URLs match exactly (http://localhost:3000 vs http://127.0.0.1:3000)

**Database Issues:**
- Delete `database.db` to reset
- Restart backend to trigger `init_db()`

**API Verification Fails:**
- Check network connectivity
- Verify API key format
- Check backend logs for error details
- Ensure timeout isn't reached (10s default)
