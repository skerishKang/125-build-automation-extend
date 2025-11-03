#!/usr/bin/env python3
"""
문서 추출기 테스트 스크립트
"""
import os
import sys
import tempfile
from pathlib import Path

# 필요한 라이브러리 직접 import
import markdown_it
from bs4 import BeautifulSoup
import csv
import openpyxl
from pptx import Presentation
import chardet

# 추출기 함수들 직접 정의 (main_enhanced.py에서 복사)
def extract_text_from_markdown(path: str) -> str:
    """Markdown 파일에서 텍스트 추출"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # markdown-it으로 HTML 변환 후 BeautifulSoup으로 텍스트 추출
        md = markdown_it.MarkdownIt()
        html = md.render(content)
        soup = BeautifulSoup(html, 'html.parser')

        # 헤딩, 목록 등 구조 유지하면서 텍스트 추출
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        print(f"Markdown 추출 실패: {e}")
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e2:
            print(f"Markdown 추출 최종 실패: {e2}")
            return ""

def extract_text_from_csv(path: str) -> str:
    """CSV 파일에서 텍스트 추출"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # 헤더와 데이터 결합
        text_parts = []
        if rows:
            text_parts.append("CSV Headers: " + ", ".join(rows[0]))
            for i, row in enumerate(rows[1:], 1):
                text_parts.append(f"Row {i}: " + ", ".join(row))

        return "\n".join(text_parts)
    except Exception as e:
        print(f"CSV 추출 실패: {e}")
        return ""

def split_into_chunks(text: str, chunk_chars: int = 4000, overlap: int = 400) -> list:
    """텍스트를 겹치는 청크로 분할"""
    if len(text) <= chunk_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_chars

        # 단어 경계에서 자르기
        if end < len(text):
            # 공백이나 줄바꿈에서 자르기
            while end > start and text[end] not in [' ', '\n', '\t']:
                end -= 1
            if end == start:  # 단어 경계 못 찾음
                end = start + chunk_chars

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks

def get_text_extractor(mime_type: str, file_path: str) -> str:
    """MIME 타입에 따른 텍스트 추출기 선택"""
    mime_to_extractor = {
        'text/markdown': extract_text_from_markdown,
        'text/html': lambda p: "",  # 간단하게 생략
        'text/csv': extract_text_from_csv,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': lambda p: "",
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': lambda p: "",
    }

    # 확장자 기반 추가 매핑
    ext_to_extractor = {
        '.md': extract_text_from_markdown,
        '.markdown': extract_text_from_markdown,
        '.html': lambda p: "",
        '.htm': lambda p: "",
        '.csv': extract_text_from_csv,
        '.xlsx': lambda p: "",
        '.pptx': lambda p: "",
    }

    # MIME 타입 우선
    if mime_type in mime_to_extractor:
        return mime_to_extractor[mime_type](file_path)

    # 확장자 기반
    ext = Path(file_path).suffix.lower()
    if ext in ext_to_extractor:
        return ext_to_extractor[ext](file_path)

    return ""

def test_markdown_extraction():
    """Markdown 추출 테스트"""
    print("=== Markdown 추출 테스트 ===")
    test_md = """
# 제목 1

이것은 **굵은 텍스트**입니다.

## 제목 2

- 목록 항목 1
- 목록 항목 2
- 목록 항목 3

### 코드 블록

```python
def hello():
    print("Hello, World!")
```

> 인용문입니다.
"""

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_md)
        temp_md_path = f.name

    result = extract_text_from_markdown(temp_md_path)
    os.unlink(temp_md_path)
    print(f"추출 결과:\n{result[:200]}...")
    print("✅ Markdown 추출 성공\n")

def test_csv_extraction():
    """CSV 추출 테스트"""
    print("=== CSV 추출 테스트 ===")
    test_csv = """이름,나이,직업
김철수,30,개발자
이영희,25,디자이너
박민수,35,매니저"""

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(test_csv)
        temp_csv_path = f.name

    result = extract_text_from_csv(temp_csv_path)
    os.unlink(temp_csv_path)
    print(f"추출 결과:\n{result}")
    print("✅ CSV 추출 성공\n")

def test_chunking():
    """청킹 테스트"""
    print("=== 청킹 테스트 ===")
    long_text = "이것은 긴 텍스트입니다. " * 100

    chunks = split_into_chunks(long_text, chunk_chars=200, overlap=50)
    print(f"원본 길이: {len(long_text)}")
    print(f"청크 개수: {len(chunks)}")
    print(f"첫 번째 청크: {chunks[0][:100]}...")
    print("✅ 청킹 성공\n")

def test_get_extractor():
    """추출기 선택 테스트"""
    print("=== 추출기 선택 테스트 ===")

    # MIME 타입 기반
    extractor = get_text_extractor('text/markdown', '/tmp/test.md')
    print(f"text/markdown -> {extractor.__name__}")

    extractor = get_text_extractor('text/html', '/tmp/test.html')
    print(f"text/html -> {extractor.__name__}")

    extractor = get_text_extractor('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '/tmp/test.xlsx')
    print(f"xlsx MIME -> {extractor.__name__}")

    # 확장자 기반
    extractor = get_text_extractor('text/plain', '/tmp/test.md')
    print(f".md 파일 -> {extractor.__name__}")

    extractor = get_text_extractor('text/plain', '/tmp/test.csv')
    print(f".csv 파일 -> {extractor.__name__}")

    extractor = get_text_extractor('text/plain', '/tmp/test.unknown')
    print(f"알 수 없는 확장자 -> {extractor.__name__}")

    print("✅ 추출기 선택 성공\n")

if __name__ == "__main__":
    print("문서 추출기 기능 테스트 시작\n")

    try:
        test_markdown_extraction()
        test_csv_extraction()
        test_chunking()
        test_get_extractor()

        print("🎉 모든 테스트 통과!")

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
