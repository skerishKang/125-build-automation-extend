"""메인 봇에서 공용으로 사용하는 상수 모음."""
from __future__ import annotations

from typing import Dict, List

GMAIL_KEYWORDS = ["gmail", "메일", "이메일", "mail", "편지", "email"]
CALENDAR_KEYWORDS = ["일정", "schedule", "calendar", "캘린더", "약속", "meeting", "회의", "모임", "event"]
CALENDAR_ADD_KEYWORDS = [
    "등록",
    "추가",
    "잡아",
    "잡아줘",
    "만들어",
    "넣어",
    "일정잡아",
    "일정잡아줘",
    "등록해",
    "등록해줘",
    "추가해",
    "추가해줘",
    "예약해줘",
    "일정만들어",
]
DRIVE_KEYWORDS = [
    "drive",
    "드라이브",
    "구글드라이브",
    "google drive",
    "google드라이브",
]
REMINDER_KEYWORDS = [
    "remind",
    "알림",
    "리마인드",
    "알려줘",
    "깨워줘",
]
SETTINGS_KEYWORDS = ["설정", "preferences", "환경설정", "세팅"]
BOTS_KEYWORDS = ["전문봇", "봇 목록", "봇상태", "bot status", "bots"]
SETTINGS_UNDO_KEYWORDS = ["되돌려", "원래", "undo", "취소", "revert"]
NOTION_REQUEST_KEYWORDS = ["노션", "notion", "기록해", "페이지"]
INTEGRATION_KEYWORDS: Dict[str, List[str]] = {
    "slack": ["슬랙", "slack"],
    "notion": ["노션", "notion"],
}
ENABLE_KEYWORDS = ["켜", "켜줘", "활성", "on", "enable", "사용", "켜라"]
DISABLE_KEYWORDS = ["꺼", "끄", "비활성", "off", "disable", "중지", "멈춰"]

GMAIL_REQUEST_VERBS = [
    "해줘",
    "해주세요",
    "해줄래",
    "알려줘",
    "알려주세요",
    "알려줄래",
    "보여줘",
    "보여주세요",
    "보여줄래",
    "읽어줘",
    "읽어주세요",
    "읽어줄래",
    "확인해줘",
    "확인해줘요",
    "확인해",
    "확인해줄래",
    "확인해 주세요",
    "가져와",
    "check",
    "show",
    "fetch",
    "list",
    "display",
]

CALENDAR_REQUEST_VERBS = [
    "해줘",
    "해주세요",
    "알려줘",
    "알려주세요",
    "보여줘",
    "보여주세요",
    "확인해줘",
    "확인해",
    "정리해줘",
    "찾아줘",
    "검색해줘",
    "추가해줘",
    "추가해",
    "등록해줘",
    "등록해",
    "예약해줘",
    "예약해",
    "check",
    "show",
    "fetch",
    "find",
    "schedule",
    "add",
]

DRIVE_REQUEST_VERBS = [
    "해줘",
    "해주세요",
    "알려줘",
    "알려주세요",
    "보여줘",
    "보여주세요",
    "확인해줘",
    "확인해",
    "목록",
    "리스트",
    "list",
    "sync",
    "동기화",
    "업데이트",
    "새",
    "신규",
    "찾아줘",
    "검색",
]

REMINDER_REQUEST_VERBS = ["해줘", "해주세요", "알려줘", "알려주세요", "보내줘", "보내주세요", "설정", "set", "remind"]
SETTINGS_REQUEST_VERBS = ["열어줘", "열어", "보여줘", "보여", "설정", "manage"]
BOTS_REQUEST_VERBS = ["알려줘", "보여줘", "확인", "status"]

TASK_TYPE_LABELS = {
    "document": "문서",
    "image": "이미지",
    "audio": "오디오",
}

TASK_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "document": ["문서", "document", "파일", "docs"],
    "image": ["이미지", "사진", "image", "photo"],
    "audio": ["오디오", "음성", "녹음", "audio", "voice"],
}

ACTION_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "document": {
        "document_original": ["원본", "원본만", "original"],
        "document_summary": ["요약", "summary", "요약만"],
        "document_original_summary": ["모두", "전체", "원본과", "풀", "full"],
        "none": ["없어", "하지마", "건너뛰", "skip", "묻지말고"],
    },
    "image": {
        "image_original": ["원본", "original"],
        "image_summary": ["분석", "설명", "텍스트", "analysis"],
        "image_original_summary": ["모두", "전체", "원본과", "풀", "full"],
        "none": ["없어", "하지마", "건너뛰", "skip", "묻지말고"],
    },
    "audio": {
        "audio_original": ["원본", "original"],
        "audio_summary": ["전사", "요약", "텍스트", "transcript", "summary"],
        "audio_original_summary": ["모두", "전체", "원본과", "풀", "full"],
        "none": ["없어", "하지마", "건너뛰", "skip", "묻지말고"],
    },
}

MODE_KEYWORDS: Dict[str, List[str]] = {
    "auto": ["자동", "auto", "항상 실행", "묻지", "바로"],
    "ask": ["묻고", "대화형", "질문", "ask"],
    "skip": ["건너", "skip", "요약만", "보고만"],
}

PIPELINE_PRESET_LABELS = {
    "full": "원본+요약 모두 저장",
    "summary": "요약 결과만 저장",
    "original": "원본 파일만 저장",
}

PIPELINE_PRESETS: Dict[str, Dict[str, str]] = {
    "full": {
        "document": "document_original_summary",
        "image": "image_original_summary",
        "audio": "audio_original_summary",
    },
    "summary": {
        "document": "document_summary",
        "image": "image_summary",
        "audio": "audio_summary",
    },
    "original": {
        "document": "document_original",
        "image": "image_original",
        "audio": "audio_original",
    },
}

FOLLOWUP_PROMPTS = {
    "document": (
        "📄 문서 분석이 완료되었습니다!\n"
        "후속 작업을 선택해주세요.\n"
        "- Drive에 원본 저장\n"
        "- 요약 텍스트 저장\n"
        "- 아무 작업하지 않기"
    ),
    "image": (
        "🖼️ 이미지 분석이 완료되었습니다!\n"
        "후속 작업을 선택해주세요.\n"
        "- 원본 이미지를 Drive에 저장\n"
        "- 설명/분석 텍스트 저장\n"
        "- 아무 작업하지 않기"
    ),
    "audio": (
        "🎤 오디오 분석이 완료되었습니다!\n"
        "후속 작업을 선택해주세요.\n"
        "- 원본 오디오 파일 저장\n"
        "- 전사/요약 텍스트 저장\n"
        "- 아무 작업하지 않기"
    ),
}
