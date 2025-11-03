"""
Google OAuth2 인증 라우터
사용자 로그인/회원가입/로그아웃을 처리합니다.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from backend.models.user import User, get_db
from backend.utils.crypto import get_crypto_manager
import os
import secrets


router = APIRouter()


# OAuth 클라이언트 설정
oauth = OAuth()

# Google OAuth2 등록
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    authorize_params={
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    },
    token_url='https://oauth2.googleapis.com/token',
    jwk_url='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={'scope': 'openid email profile'}
)


@router.get('/login')
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth 로그인 시작점
    
    프론트엔드에서 호출하면 사용자가 Google 로그인 페이지로 리다이렉트됩니다.
    """
    # CSRF 방지를 위한 state 생성
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Google 인증 페이지로 리다이렉트
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@router.get('/callback')
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google OAuth 콜백 처리
    
    Google에서 사용자 정보를 반환하면 이를 처리하여 데이터베이스에 저장/로그인 처리합니다.
    """
    try:
        # state 검증
        state = request.query_params.get('state')
        if state != request.session.get('oauth_state'):
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # 토큰 교환
        token = await oauth.google.authorize_access_token(request)
        
        # 사용자 정보 조회
        user_info = await oauth.google.userinfo(token)
        
        # 데이터베이스에서 사용자 조회 또는 생성
        user = db.query(User).filter(User.google_id == user_info['sub']).first()
        
        if not user:
            # 새 사용자 생성
            user = User(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=user_info['name'],
                picture=user_info.get('picture', '')
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # 기존 사용자 정보 업데이트
            user.name = user_info['name']
            user.picture = user_info.get('picture', '')
            user.email = user_info['email']
            db.commit()

        # 세션에 사용자 ID 저장
        request.session['user_id'] = user.id
        request.session['user_email'] = user.email
        
        # 프론트엔드로 리다이렉트
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/dashboard")

    except Exception as e:
        print(f"Auth error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get('/me')
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    현재 로그인된 사용자 정보 반환
    
    프론트엔드에서 세션 상태 확인용으로 사용됩니다.
    """
    user_id = request.session.get('user_id')
    
    if not user_id:
        return JSONResponse(
            content={'authenticated': False, 'user': None},
            status_code=401
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return JSONResponse(
            content={'authenticated': False, 'user': None},
            status_code=401
        )
    
    return {
        'authenticated': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'picture': user.picture
        }
    }


@router.post('/logout')
async def logout(request: Request):
    """
    로그아웃 처리
    
    세션을 제거하고 로그인 페이지로 리다이렉트합니다.
    """
    request.session.clear()
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    return RedirectResponse(url=f"{frontend_url}/")
