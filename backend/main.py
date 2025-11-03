"""
125 Build Automation Extend - FastAPI 백엔드 서버
API 키 검증 + AI 문서 분석 통합 버전
"""
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import verify_keys
from backend.models.user import init_db
from backend.services.ai_service import (
    summarize_text,
    analyze_document,
    rag_answer,
    health_check as ai_health_check
)
import os
import tempfile
import chardet
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("backend.log", maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# 콘솔 로거
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# FastAPI 앱 생성
app = FastAPI(
    title="125 Build Automation Extend API",
    description=""" \
    API 키 검증 + AI 문서 분석 통합 서비스

    ### 주요 기능
    - 서비스별 API 키 검증 (Telegram, Slack)
    - Gemini AI 기반 문서 요약 및 분석
    - RAG (검색 증강 생성) 기반 질의응답
    - 다양한 파일 형식 지원 (PDF, DOCX, TXT, MD, CSV, etc.)

    ### 지원 서비스
    - Telegram Bot Token 검증
    - Slack Bot Token 검증
    - 문서 업로드 및 AI 분석
    """,
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS 미들웨어 설정
# 환경변수에서 허용 오리진 목록 읽기 (콤마로 구분)
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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


# ===== AI 문서 분석 엔드포인트 =====

@app.post("/api/summarize")
async def summarize_document(file: UploadFile = File(...)):
    """문서 요약"""
    try:
        # 파일 읽기
        content = await file.read()

        # 텍스트 추출
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        text = extract_text_from_file(content, file_ext)

        if not text:
            raise HTTPException(status_code=400, detail="텍스트를 추출할 수 없습니다")

        # 요약
        summary = summarize_text(text, file.filename or "Document")
        return {"summary": summary}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 실패: {str(e)}")


@app.post("/api/analyze")
async def analyze_document_endpoint(file: UploadFile = File(...)):
    """문서 분석"""
    try:
        # 파일 읽기
        content = await file.read()

        # 텍스트 추출
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        text = extract_text_from_file(content, file_ext)

        if not text:
            raise HTTPException(status_code=400, detail="텍스트를 추출할 수 없습니다")

        # 분석
        analysis = analyze_document(text, file.filename or "Document")
        return {"analysis": analysis}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@app.post("/api/qa")
async def qa_endpoint(query: str, user_id: str = "default"):
    """RAG 질의응답"""
    try:
        answer = rag_answer(query, user_id)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질의응답 실패: {str(e)}")


@app.get("/api/health")
async def ai_health():
    """AI 서비스 상태 확인"""
    return ai_health_check()


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
        'message': '125 Build Automation Extend API is running',
        'version': '0.3.0',
        'features': ['api_key_verification', 'ai_document_analysis']
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
        'version': '0.3.0',
        'docs': '/docs',
        'health': '/health',
        'verify': '/verify',
        'ai': {
            'summarize': '/api/summarize',
            'analyze': '/api/analyze',
            'qa': '/api/qa',
            'health': '/api/health'
        }
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
        'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:3000'),
        'telegram_token_set': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
        'gemini_api_key_set': bool(os.getenv('GEMINI_API_KEY')),
        'rag_enabled': os.getenv('USE_RAG', 'false').lower() == 'true'
    }


# ===== 유틸리티 함수 =====

def extract_text_from_file(content: bytes, file_ext: str) -> str:
    """파일에서 텍스트 추출 (기본 구현)"""
    try:
        # 텍스트 파일인 경우
        if file_ext in ['.txt', '.log', '.md', '.json', '.xml', '.csv']:
            # 인코딩 감지
            detected = chardet.detect(content)
            encoding = detected.get('encoding', 'utf-8')

            # 텍스트 디코딩
            text = content.decode(encoding, errors='ignore')
            return text

        # 기타 파일은 기본 텍스트로 처리
        return content.decode('utf-8', errors='ignore')

    except Exception as e:
        print(f"텍스트 추출 실패: {e}")
        return ""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        # Run from project root so package imports like `backend.*` resolve
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
