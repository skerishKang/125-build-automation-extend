"""
125 Build Automation Extend - FastAPI 백엔드 서버
단순 API 키 검증 버전 (인증 없음)
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import verify_keys
from backend.models.user import init_db
import os
from dotenv import load_dotenv


# 환경변수 로드
load_dotenv()


# FastAPI 앱 생성
app = FastAPI(
    title="125 Build Automation Extend API",
    description=""" \
    단순 API 키 검증 서비스 (인증 없음 버전)

    ### 주요 기능
    - 서비스별 API 키 등록 및 검증 (Telegram, Slack)
    - AES256 암호화를 통한 보안 저장
    - 실시간 검증

    ###支持的 서비스
    - Telegram Bot Token
    - Slack Bot Token
    """,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)




# CORS 미들웨어 설정
# 프론트엔드 도메인에서 API 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        os.getenv("FRONTEND_URL", "http://localhost:3002")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# 라우터 등록
app.include_router(
    verify_keys.router,
    prefix="/verify",
    tags=["API Key Verification"]
)


# 데이터베이스 초기화
@app.on_event("startup")
async def startup_event():
    """서버 시작시 데이터베이스 테이블 생성"""
    init_db()
    print("Database initialized")


# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """
    서버 상태 확인 엔드포인트

    Returns:
        {'status': 'ok'}
    """
    return {
        'status': 'ok',
        'message': '125 Build Automation Extend API is running'
    }


# 루트 엔드포인트
@app.get("/")
async def root():
    """
    API 정보 반환

    Returns:
        API 기본 정보
    """
    return {
        'name': '125 Build Automation Extend API',
        'version': '0.1.0',
        'docs': '/docs',
        'health': '/health',
        'verify': '/verify'
    }


# 개발용: 현재 설정된 환경변수 확인 (실제 값은 표시하지 않음)
@app.get("/config")
async def check_config():
    """환경변수 설정 상태 확인 (개발용)"""
    return {
        'google_client_id_set': bool(os.getenv('GOOGLE_CLIENT_ID')),
        'google_client_secret_set': bool(os.getenv('GOOGLE_CLIENT_SECRET')),
        'aes_key_set': bool(os.getenv('AES_KEY')),
        'database_url_set': bool(os.getenv('DATABASE_URL')),
        'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:3000')
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        # Run from project root so package imports like `backend.*` resolve
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
