"""텍스트 가공 유틸리티.

메인 봇 및 하위 핸들러에서 공통으로 사용하는 Markdown 정리, 문자열 분할,
이메일 포맷팅 등의 기능을 제공한다.
"""
from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List


_MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s*", flags=re.MULTILINE)
_BOLD_PATTERN = re.compile(r"(\*\*|__)(.*?)(?:\1)")
_INLINE_CODE_PATTERN = re.compile(r"`(.+?)`")


def simplify_markdown(text: str) -> str:
    """Markdown을 텔레그램 친화적인 일반 텍스트로 정리한다."""

    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n")
    cleaned = _MARKDOWN_HEADING_PATTERN.sub("", cleaned)
    cleaned = _BOLD_PATTERN.sub(r"\2", cleaned)
    cleaned = _INLINE_CODE_PATTERN.sub(r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = cleaned.replace("* ", "- ")
    cleaned = cleaned.replace("\t", "    ")
    return cleaned.strip()


def split_into_chunks(text: str, limit: int = 3500) -> List[str]:
    """텔레그램 메시지 길이 제한에 맞게 문자열을 분할한다."""

    if not text:
        return []
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def format_duration(seconds: int) -> str:
    """초 단위 시간을 한국어로 읽기 쉬운 형태로 변환한다."""

    if seconds < 60:
        return f"{seconds}초"

    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if remaining_seconds > 0:
        return f"{minutes}분 {remaining_seconds}초"

    return f"{minutes}분"


def format_email_entry(email: Dict[str, Any], index: int) -> str:
    """이메일 정보를 사람이 읽기 쉬운 문자열로 변환한다."""

    sender = email.get("sender", "알 수 없음")
    subject = email.get("subject", "제목 없음")
    date_str = email.get("date", "")
    formatted_date = "날짜 정보 없음"

    if date_str:
        try:
            email_dt = parsedate_to_datetime(date_str)
            if email_dt.tzinfo is None:
                email_dt = email_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            formatted_date = email_dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            formatted_date = date_str

    body_preview = simplify_markdown(email.get("body", "")).strip()
    if len(body_preview) > 200:
        body_preview = body_preview[:200] + "..."
    if not body_preview:
        body_preview = "(본문 없음)"

    lines = [
        f"{index}. ✉️ {subject}",
        f"   보낸 사람: {sender}",
        f"   받은 시간: {formatted_date}",
        f"   미리보기: {body_preview}",
    ]
    return "\n".join(lines)
