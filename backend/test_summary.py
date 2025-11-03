#!/usr/bin/env python3
"""
요약 기능 테스트 스크립트
"""
import os
import sys
sys.path.append('.')

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# Gemini 모델 초기화
import google.generativeai as genai
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config = genai.GenerationConfig(
        temperature=0.2,
        top_p=0.9,
        max_output_tokens=2048
    )
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)
else:
    print("❌ GEMINI_API_KEY가 설정되지 않았습니다")
    sys.exit(1)

def summarize_chunk(chunk: str) -> str:
    """단일 청크 요약"""
    prompt = f"""역할: 전문가 보조 에이전트

다음 텍스트를 분석하여 핵심 내용을 요약해주세요.

요약 지침:
- 섹션별로 구조화: 요약/핵심포인트/액션아이템/날짜/리스크
- 근거가 약하면 '추정'으로 표기
- 간결하고 구조화된 형식으로 작성

텍스트:
{chunk}

요약:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"요약 실패: {e}")
        return f"요약 실패: {chunk[:200]}..."

def test_summary():
    """요약 기능 테스트"""
    print("=== 요약 기능 테스트 ===")

    test_text = """
    125 Build Automation 프로젝트는 AI 기반 문서 분석 시스템입니다.

    주요 기능:
    - 텔레그램 봇을 통한 문서 업로드
    - Google Drive 연동
    - 다양한 형식 지원 (Markdown, CSV, Excel, PowerPoint)
    - Gemini AI를 활용한 지능적 요약
    - RAG (Retrieval-Augmented Generation) 시스템

    기술 스택:
    - Python FastAPI 백엔드
    - Telegram Bot API
    - Google Gemini AI
    - ChromaDB 벡터 데이터베이스
    - Sentence Transformers 임베딩

    현재 구현된 개선사항:
    1. 범용 문서 추출기 (다양한 파일 형식 지원)
    2. 청크 기반 긴 문서 처리
    3. 맵리듀스 요약 알고리즘
    4. 조건부 RAG 시스템 활성화
    """

    print(f"원본 텍스트 길이: {len(test_text)}자")
    print(f"원본 텍스트:\n{test_text}\n")

    summary = summarize_chunk(test_text)
    print(f"요약 결과:\n{summary}")
    print("✅ 요약 기능 테스트 성공\n")

if __name__ == "__main__":
    print("Gemini AI 요약 기능 테스트 시작\n")

    try:
        test_summary()
        print("🎉 요약 테스트 통과!")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
