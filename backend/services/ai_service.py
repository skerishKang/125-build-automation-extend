"""
AI 서비스 모듈
Gemini AI를 활용한 문서 요약 및 RAG 질의응답
"""
import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# 환경변수
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
USE_RAG = os.getenv('USE_RAG', 'false').lower() == 'true'
VECTOR_STORE_PATH = os.getenv('VECTOR_STORE_PATH', 'data/store')
GEN_TEMPERATURE = float(os.getenv('GEN_TEMPERATURE', '0.2'))
GEN_MAX_OUTPUT_TOKENS = int(os.getenv('GEN_MAX_OUTPUT_TOKENS', '2048'))

# Gemini 모델 초기화 (API 키가 있을 때만)
model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        generation_config = genai.GenerationConfig(
            temperature=GEN_TEMPERATURE,
            top_p=0.9,
            max_output_tokens=GEN_MAX_OUTPUT_TOKENS
        )
        model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            generation_config=generation_config
        )
        logger.info("Gemini AI 모델 초기화 완료")
    except ImportError as e:
        logger.error(f"google-generativeai 모듈을 찾을 수 없습니다: {e}")
        logger.error("pip install google-generativeai를 실행해주세요")
    except Exception as e:
        logger.error(f"Gemini AI 초기화 실패: {e}")

# RAG 관련 모듈 (선택적 로딩)
faiss = None
chromadb = None
SentenceTransformer = None
vector_store = None
embedding_model = None

if USE_RAG:
    try:
        import faiss
        import chromadb
        from sentence_transformers import SentenceTransformer

        # 임베딩 모델 초기화
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # 벡터 스토어 초기화
        import os
        os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
        vector_store = chromadb.PersistentClient(path=VECTOR_STORE_PATH)

        logger.info("RAG 시스템 초기화 완료")
    except ImportError as e:
        logger.warning(f"RAG 관련 모듈 import 실패: {e}")
        logger.warning("필요시: pip install faiss-cpu chromadb sentence-transformers")


def split_into_chunks(text: str, chunk_chars: int = 4000, overlap: int = 400) -> List[str]:
    """텍스트를 겹치는 청크로 분할"""
    if len(text) <= chunk_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_chars

        # 단어 경계에서 자르기
        if end < len(text):
            while end > start and text[end] not in [' ', '\n', '\t']:
                end -= 1
            if end == start:
                end = start + chunk_chars

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def summarize_text(text: str, file_name: str = "Document") -> str:
    """문서 요약"""
    if not model:
        return "❌ Gemini AI가 초기화되지 않았습니다. GEMINI_API_KEY를 확인해주세요."

    if not text or len(text.strip()) == 0:
        return "❌ 빈 문서입니다."

    try:
        # 긴 문서는 청크로 분할
        if len(text) > 8000:
            chunks = split_into_chunks(text, chunk_chars=4000)
            chunk_summaries = []

            for i, chunk in enumerate(chunks):
                prompt = f"""다음 텍스트를 분석하여 핵심 내용을 요약해주세요.

요약 지침:
- 섹션별로 구조화: 요약/핵심포인트/액션아이템/날짜/리스크
- 근거가 약하면 '추정'으로 표기
- 간결하고 구조화된 형식으로 작성

문서: {file_name} (파트 {i+1}/{len(chunks)})
텍스트:
{chunk[:3000]}

요약:"""

                response = model.generate_content(prompt)
                chunk_summaries.append(f"**파트 {i+1}:**\n{response.text.strip()}")

            # 통합 요약
            combined_summaries = "\n\n".join(chunk_summaries)

            final_prompt = f"""다음은 여러 파트의 요약입니다. 이를 종합하여 전체 문서의 통합 요약을 작성해주세요.

통합 요약 지침:
- 전체 문서의 주요 테마와 내용을 포괄
- 섹션별 구조화 유지
- 중복 제거 및 일관성 확보
- 핵심 인사이트 강조

파트 요약들:
{combined_summaries}

최종 통합 요약:"""

            response = model.generate_content(final_prompt)
            return response.text.strip()

        else:
            # 단일 패스 요약
            prompt = f"""역할: 전문 문서 분석가

다음 문서를 전문적으로 분석하고 요약해주세요.

분석 요구사항:
- 문서의 주요 목적과 내용 파악
- 핵심 개념과 주요 포인트 도출
- 구조화된 요약 형식으로 정리

문서 정보:
- 파일명: {file_name}
- 길이: {len(text)}자

문서 내용:
{text[:5000]}

분석 및 요약:"""

            response = model.generate_content(prompt)
            return response.text.strip()

    except Exception as e:
        logger.error(f"문서 요약 실패: {e}")
        return f"❌ 요약 중 오류 발생: {str(e)}"


def analyze_document(text: str, file_name: str = "Document") -> str:
    """문서 분석 (상세 분석)"""
    if not model:
        return "❌ Gemini AI가 초기화되지 않았습니다. GEMINI_API_KEY를 확인해주세요."

    if not text or len(text.strip()) == 0:
        return "❌ 빈 문서입니다."

    try:
        prompt = f"""역할: 전문 문서 분석가

다음 문서를 전문적으로 분석해주세요.

분석 요구사항:
- 문서의 주요 목적과 내용 파악
- 구조와 구성 요소 분석
- 핵심 개념과 주요 포인트 도출
- 잠재적 활용 방안 제시
- 개선점이나 주의사항 언급
- SWOT 분석 (가능한 경우)

문서 정보:
- 파일명: {file_name}
- 길이: {len(text)}자

문서 내용:
{text[:6000]}

분석 결과:"""

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"문서 분석 실패: {e}")
        return f"❌ 분석 중 오류 발생: {str(e)}"


def rag_answer(query: str, owner_id: str = None, top_k: int = 3) -> str:
    """RAG 질의응답"""
    if not USE_RAG:
        return "⚠️ RAG 시스템이 비활성화되었습니다. backend/.env에서 USE_RAG=true로 설정해주세요."

    if not vector_store or not embedding_model:
        return "❌ RAG 시스템이 초기화되지 않았습니다."

    if not query or len(query.strip()) == 0:
        return "❌ 빈 질문입니다."

    try:
        # 컬렉션 가져오기
        collection_name = f"docs_{owner_id}" if owner_id else "docs_default"
        collection = vector_store.get_or_create_collection(name=collection_name)

        # 쿼리 임베딩
        query_embedding = embedding_model.encode(query).tolist()

        # 유사도 검색
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, 5)
        )

        if not results['documents'] or not results['documents'][0]:
            return "ℹ️ 관련 문서를 찾을 수 없습니다. 문서를 먼저 업로드해주세요."

        # 컨텍스트 구성
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            context_parts.append(
                f"**문서 {i+1}** ({metadata.get('file_name', 'Unknown')}):\n{doc[:500]}..."
            )

        context = "\n\n".join(context_parts)

        # 답변 생성
        prompt = f"""역할: 전문 어시스턴트

아래 참고 문서들을 근거로 질문에 답변해주세요.

답변 지침:
- 문서 근거 인용 (파일명/페이지/섹션 헤딩 포함)
- 근거가 없으면 '문서에서 해당 정보를 찾을 수 없습니다'로 응답
- 간결하고 구조화된 형식으로 작성
- 필요한 경우 목록 형태로 정리

참고 문서:
{context}

질문: {query}

답변:"""

        if not model:
            return f"❌ Gemini AI가 초기화되지 않았습니다.\n\n참고 문서:\n{context}"

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"RAG 쿼리 실패: {e}")
        return f"❌ 질의응답 중 오류 발생: {str(e)}"


def rag_store_document(file_path: str, file_name: str, text: str, owner_id: str) -> bool:
    """문서를 RAG 벡터 스토어에 저장"""
    if not USE_RAG or not vector_store or not embedding_model:
        return False

    try:
        collection_name = f"docs_{owner_id}"
        collection = vector_store.get_or_create_collection(name=collection_name)

        # 청크 분할
        chunks = split_into_chunks(text, chunk_chars=1000, overlap=100)

        # 임베딩 및 저장
        for i, chunk in enumerate(chunks):
            import hashlib
            chunk_id = f"{file_name}_{i}_{hashlib.md5(chunk.encode()).hexdigest()[:8]}"
            embedding = embedding_model.encode(chunk).tolist()

            import datetime
            metadata = {
                'file_name': file_name,
                'chunk_index': i,
                'owner_id': str(owner_id),
                'created_at': datetime.datetime.now().isoformat()
            }

            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[chunk]
            )

        logger.info(f"RAG 저장 완료: {file_name} ({len(chunks)} 청크)")
        return True

    except Exception as e:
        logger.error(f"RAG 저장 실패: {e}")
        return False


def health_check() -> Dict[str, Any]:
    """AI 서비스 상태 확인"""
    return {
        'gemini_ai': model is not None,
        'rag_enabled': USE_RAG,
        'rag_initialized': vector_store is not None and embedding_model is not None,
        'gemini_api_key': bool(GEMINI_API_KEY),
    }
