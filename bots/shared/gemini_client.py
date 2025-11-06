"""
Gemini 2.5 Flash Client - Shared AI Analysis
"""
import google.generativeai as genai
import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Optional, Union

logger = logging.getLogger("gemini_client")


class GeminiAnalyzer:
    """Shared Gemini analysis for all bots"""

    def __init__(self, api_key: str = None):
        """Initialize with specific API key"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.enabled = True
        else:
            logger.warning("Gemini API key not provided")
            self.model = None
            self.enabled = False

    def analyze_text(self, text: str, prompt: str = "") -> Optional[str]:
        """Analyze text with Gemini"""
        if not self.enabled:
            return None

        try:
            full_prompt = f"{prompt}\n\n{text}" if prompt else text
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            return None

    def analyze_image(self, image_data: bytes, prompt: str = "") -> Optional[str]:
        """Analyze image with Gemini Vision"""
        if not self.enabled:
            return None

        try:
            image_part = {"mime_type": "image/jpeg", "data": image_data}
            full_prompt = prompt or "Describe this image in detail"
            response = self.model.generate_content([full_prompt, image_part])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return None

    def analyze_audio(self, audio_data: bytes, prompt: str = "") -> Optional[str]:
        """Analyze audio with Gemini multimodal"""
        if not self.enabled:
            return None

        try:
            audio_part = {"mime_type": "audio/ogg", "data": audio_data}
            full_prompt = prompt or "Transcribe and summarize this audio"
            response = self.model.generate_content([full_prompt, audio_part])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return None

    def analyze_document(self, content: str, doc_type: str = "default") -> str:
        """Analyze document with appropriate prompt"""
        if not self.enabled:
            return "Gemini AI not configured"

        prompts = {
            "pdf": "이 PDF 문서를 분석하고 핵심 내용을 요약해주세요.",
            "docx": "이 문서를 분석하고 핵심 내용을 요약해주세요.",
            "txt": "이 텍스트를 분석하고 핵심 내용을 요약해주세요.",
            "csv": "이 데이터를 분석하고 주요 인사이트를 제공해주세요.",
            "md": "이 마크다운 문서를 분석하고 핵심 내용을 요약해주세요.",
            "html": "이 HTML 문서를 분석하고 핵심 내용을 요약해주세요.",
            "htm": "이 HTML 문서를 분석하고 핵심 내용을 요약해주세요.",
            "default": "이 문서를 분석하고 핵심 내용을 요약해주세요."
        }

        normalized_type = (doc_type or "default").lower().lstrip(".")
        prompt = prompts.get(normalized_type, prompts["default"])

        try:
            result = self.model.generate_content(f"{prompt}\n\n{content}")
            return result.text.strip()
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            return f"Error analyzing document: {str(e)}"

    def analyze_audio_transcription(self, transcription: str) -> str:
        """Analyze audio transcription"""
        if not self.enabled:
            return "Gemini AI not configured"

        prompt = """
        다음 음성 전사 텍스트를 분석해주세요:
        1. 주요 내용 요약
        2. 중요한 정보 추출
        3. 다음 단계나 액션 항목 (있다면)
        """

        try:
            result = self.model.generate_content(f"{prompt}\n\n{transcription}")
            return result.text.strip()
        except Exception as e:
            logger.error(f"Audio analysis error: {e}")
            return f"Error analyzing audio: {str(e)}"

    def analyze_image_description(self, image_source: Union[str, bytes]) -> str:
        """Analyze image and provide description."""
        if not self.enabled:
            return "Gemini AI not configured"

        prompt = """
        이 이미지를 상세히 분석해주세요:
        1. 이미지 내용 설명
        2. 주요 객체나 특징
        3. 색감이나 분위기
        4. 텍스트가 있다면 내용 (ocr)
        """

        try:
            if isinstance(image_source, bytes):
                image_data = image_source
            else:
                with open(image_source, "rb") as image_file:
                    image_data = image_file.read()

            image_part = {"mime_type": "image/jpeg", "data": image_data}

            def _generate():
                return self.model.generate_content([prompt, image_part])

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_generate)
                result = future.result(timeout=60)

            return result.text.strip()
        except FuturesTimeoutError:
            logger.error("Image analysis timed out after 60 seconds")
            return "이미지 분석 중 시간 초과가 발생했습니다."
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return f"Error analyzing image: {str(e)}"

    def analyze_image_file(self, image_path: str) -> str:
        """Analyze image (same as analyze_image_description for compatibility)"""
        return self.analyze_image_description(image_path)

    def summarize_text(self, text: str, max_length: int = 500) -> Optional[str]:
        """Summarize text with Gemini"""
        prompt = f"""
        다음 텍스트를 간결하게 요약해주세요.
        - 핵심 내용만
        - 불필요한 상세사항 제거
        - 최대 {max_length}자 이내
        """
        return self.analyze_text(text, prompt)

    def extract_key_points(self, text: str) -> Optional[str]:
        """Extract key points from text"""
        prompt = """
        다음 텍스트에서 핵심 요점 3-5가지를 추출해주세요.
        각 요점은 한 문장으로 요약.
        """
        return self.analyze_text(text, prompt)

    def translate_to_korean(self, text: str) -> Optional[str]:
        """Translate text to Korean"""
        prompt = "다음 텍스트를 한국어로 번역해주세요."
        return self.analyze_text(text, prompt)


if __name__ == "__main__":
    # Test Gemini connection
    analyzer = GeminiAnalyzer()
    if analyzer.enabled:
        try:
            response = analyzer.analyze_text("Hello")
            print("✅ Gemini connection successful")
            print(f"Test response: {response[:100]}")
        except Exception as e:
            print(f"❌ Gemini test failed: {e}")
    else:
        print("❌ Gemini not configured")
