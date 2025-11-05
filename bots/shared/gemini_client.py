"""
Gemini 2.5 Flash Client - Shared AI Analysis
"""
import google.generativeai as genai
import logging
from typing import Any, Optional

logger = logging.getLogger("gemini_client")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    logger.warning("GEMINI_API_KEY not set")
    model = None


class GeminiAnalyzer:
    """Shared Gemini analysis for all bots"""

    @staticmethod
    def analyze_text(text: str, prompt: str = "") -> Optional[str]:
        """Analyze text with Gemini"""
        if not model:
            return None

        try:
            full_prompt = f"{prompt}\n\n{text}" if prompt else text
            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return None

    @staticmethod
    def analyze_image(image_data: bytes, prompt: str = "") -> Optional[str]:
        """Analyze image with Gemini Vision"""
        if not model:
            return None

        try:
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            full_prompt = prompt or "Describe this image in detail"
            response = model.generate_content([full_prompt, image_part])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return None

    @staticmethod
    def analyze_audio(audio_data: bytes, prompt: str = "") -> Optional[str]:
        """Analyze audio with Gemini multimodal"""
        if not model:
            return None

        try:
            audio_part = {"mime_type": "audio/ogg", "data": audio_data}
            full_prompt = prompt or "Transcribe and summarize this audio"
            response = model.generate_content([full_prompt, audio_part])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return None

    @staticmethod
    def summarize_text(text: str, max_length: int = 500) -> Optional[str]:
        """Summarize text with Gemini"""
        prompt = f"""
        다음 텍스트를 간결하게 요약해주세요.
        - 핵심 내용만
        - 불필요한 상세사항 제거
        - 최대 {max_length}자 이내
        """
        return GeminiAnalyzer.analyze_text(text, prompt)

    @staticmethod
    def extract_key_points(text: str) -> Optional[str]:
        """Extract key points from text"""
        prompt = """
        다음 텍스트에서 핵심 요점 3-5가지를 추출해주세요.
        각 요점은 한 문장으로 요약.
        """
        return GeminiAnalyzer.analyze_text(text, prompt)

    @staticmethod
    def translate_to_korean(text: str) -> Optional[str]:
        """Translate text to Korean"""
        prompt = "다음 텍스트를 한국어로 번역해주세요."
        return GeminiAnalyzer.analyze_text(text, prompt)


# Convenience functions for document analysis
def analyze_document(content: str, doc_type: str) -> dict:
    """Analyze document with appropriate prompt"""
    if not model:
        return {"error": "Gemini not configured"}

    prompts = {
        "pdf": "이 PDF 문서를 분석하고 핵심 내용을 요약해주세요.",
        "docx": "이 문서를 분석하고 핵심 내용을 요약해주세요.",
        "txt": "이 텍스트를 분석하고 핵심 내용을 요약해주세요.",
        "csv": "이 데이터를 분석하고 주요 인사이트를 제공해주세요.",
        "md": "이 마크다운 문서를 분석하고 핵심 내용을 요약해주세요.",
        "default": "이 문서를 분석하고 핵심 내용을 요약해주세요."
    }

    prompt = prompts.get(doc_type.lower(), prompts["default"])

    try:
        result = model.generate_content(f"{prompt}\n\n{content}")
        text = result.text.strip()

        return {
            "summary": text[:500],
            "full_analysis": text,
            "word_count": len(text.split()),
            "doc_type": doc_type
        }
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        return {"error": str(e)}


# Convenience functions for audio analysis
def analyze_audio_transcription(transcription: str) -> dict:
    """Analyze audio transcription"""
    if not model:
        return {"error": "Gemini not configured"}

    prompt = """
    다음 음성 전사 텍스트를 분석해주세요:
    1. 주요 내용 요약
    2. 중요한 정보 추출
    3. 다음 단계나 액션 항목 (있다면)
    """

    try:
        result = model.generate_content(f"{prompt}\n\n{transcription}")
        text = result.text.strip()

        return {
            "summary": text[:500],
            "full_analysis": text,
            "duration_estimate": len(transcription) // 10  # rough estimate
        }
    except Exception as e:
        logger.error(f"Audio analysis error: {e}")
        return {"error": str(e)}


# Convenience functions for image analysis
def analyze_image_description(image_data: bytes) -> dict:
    """Analyze image and provide description"""
    if not model:
        return {"error": "Gemini not configured"}

    prompt = """
    이 이미지를 상세히 분석해주세요:
    1. 이미지 내용 설명
    2. 주요 객체나 특징
    3. 색감이나 분위기
    4. 텍스트가 있다면 내용 (ocr)
    """

    try:
        image_part = {"mime_type": "image/jpeg", "data": image_data}
        result = model.generate_content([prompt, image_part])
        text = result.text.strip()

        return {
            "description": text[:500],
            "full_analysis": text,
            "image_size": len(image_data)
        }
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test Gemini connection
    if model:
        try:
            response = model.generate_content("Hello")
            print("✅ Gemini connection successful")
            print(f"Test response: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Gemini test failed: {e}")
    else:
        print("❌ Gemini not configured")
