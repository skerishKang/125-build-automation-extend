"""메인 봇 자연어 명령 파싱 유틸리티."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..constants import (
    ACTION_KEYWORDS,
    BOTS_KEYWORDS,
    BOTS_REQUEST_VERBS,
    CALENDAR_ADD_KEYWORDS,
    CALENDAR_KEYWORDS,
    CALENDAR_REQUEST_VERBS,
    DISABLE_KEYWORDS,
    DRIVE_KEYWORDS,
    DRIVE_REQUEST_VERBS,
    ENABLE_KEYWORDS,
    GMAIL_KEYWORDS,
    GMAIL_REQUEST_VERBS,
    INTEGRATION_KEYWORDS,
    MODE_KEYWORDS,
    NOTION_REQUEST_KEYWORDS,
    PIPELINE_PRESETS,
    REMINDER_KEYWORDS,
    REMINDER_REQUEST_VERBS,
    SETTINGS_KEYWORDS,
    SETTINGS_REQUEST_VERBS,
    SETTINGS_UNDO_KEYWORDS,
    TASK_TYPE_KEYWORDS,
)
from ..utils.datetime_utils import parse_relative_date_time


def _contains_intent_phrase(lowered: str, compact: str, phrases: List[str]) -> bool:
    for phrase in phrases:
        phrase_lower = phrase.lower()
        if phrase_lower in lowered or phrase_lower in compact:
            return True
    return False


def _normalize_text(text: str) -> str:
    return re.sub(r"[\s]+", " ", text.lower()).strip()


def _match_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_event_title(original_text: str) -> str:
    removal_patterns = [
        r"(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(에|에서|부터|까지)?",
        r"(\d{1,2})/(\d{1,2})\s*(에|에서|부터|까지)?",
        r"(\d{1,2})\s*시\s*(\d{0,2})?\s*분?\s*(에|에서|부터|까지)?",
        r"(\d{1,2}):(\d{2})\s*(에|에서|부터|까지)?",
    ]
    removal_words = [
        "등록해줘",
        "등록해",
        "추가해줘",
        "추가해",
        "잡아줘",
        "잡아",
        "예약해줘",
        "예약해",
        "해주세요",
        "해줘",
        "해줄래",
        "부탁",
        "달력",
        "캘린더",
        "등록",
        "추가",
        "만들어",
        "오늘",
        "내일",
        "모레",
        "다가오는",
        "곧",
        "이번주",
        "이번 주",
        "week",
        "today",
        "tomorrow",
        "am",
        "pm",
    ]

    text = original_text
    for pattern in removal_patterns:
        text = re.sub(pattern, " ", text)
    for word in removal_words:
        text = text.replace(word, " ")

    summary = re.sub(r"\s+", " ", text).strip()
    if not summary:
        summary = "일정"
    return summary


def detect_gmail_command(lowered: str, compact: str, original: str) -> Optional[Dict[str, Any]]:
    if any(keyword in lowered for keyword in GMAIL_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, GMAIL_REQUEST_VERBS):
            args: List[str] = []
            count = None
            korean_numbers = {
                "하나": 1,
                "일": 1,
                "두개": 2,
                "둘": 2,
                "이": 2,
                "세개": 3,
                "셋": 3,
                "삼": 3,
                "네개": 4,
                "넷": 4,
                "사": 4,
                "다섯개": 5,
                "다섯": 5,
                "오": 5,
                "여섯개": 6,
                "여섯": 6,
                "육": 6,
                "일곱개": 7,
                "일곱": 7,
                "칠": 7,
                "여덟개": 8,
                "여덟": 8,
                "팔": 8,
                "아홉개": 9,
                "아홉": 9,
                "구": 9,
                "열개": 10,
                "열": 10,
                "십": 10,
            }
            for korean_num in korean_numbers:
                if korean_num in lowered:
                    count = korean_numbers[korean_num]
                    break
            if not count:
                count_match = re.search(r"(\d{1,2})\s*(개|건|통|mail|mails|message|messages)?", lowered)
                if count_match:
                    try:
                        count = max(1, min(int(count_match.group(1)), 10))
                    except ValueError:
                        count = None
            if count:
                args.append(str(count))
            if any(word in lowered for word in ["읽음", "읽어", "읽어줘", "읽은", "mark", "읽기", "읽음처리", "mark read"]):
                args.append("mark")
            if any(word in lowered for word in ["최근", "latest", "recent", "모두", "전부", "전체", "all"]):
                args.append("all")
            return {"command": "gmail", "args": args}
    return None


def detect_calendar_command(lowered: str, compact: str, original: str) -> Optional[Dict[str, Any]]:
    if any(keyword in lowered for keyword in CALENDAR_ADD_KEYWORDS) and any(keyword in lowered for keyword in CALENDAR_KEYWORDS + ["일정", "모임", "회의"]):
        if _contains_intent_phrase(lowered, compact, CALENDAR_REQUEST_VERBS):
            parsed = parse_relative_date_time(original)
            if parsed:
                summary = extract_event_title(original)
                event_info = {
                    "summary": summary,
                    "start": parsed["start"],
                    "end": parsed["end"],
                    "duration_minutes": parsed["duration_minutes"],
                }
                return {"command": "calendar_add", "event_info": event_info}
    if any(keyword in lowered for keyword in CALENDAR_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, CALENDAR_REQUEST_VERBS):
            args: List[str] = []
            query = None
            if any(word in lowered for word in ["내일", "tomorrow", "tmr"]):
                args.append("tomorrow")
            elif any(word in lowered for word in ["이번주", "이번 주", "주간", "week"]):
                args.append("week")
            elif any(word in lowered for word in ["오늘", "today"]):
                args.append("today")
            elif any(word in lowered for word in ["다가오는", "곧", "soon", "upcoming", "예정"]):
                minutes = 60
                minute_match = re.search(r"(\d{1,3})\s*(분|min|minute|minutes)", lowered)
                if minute_match:
                    try:
                        minutes = max(10, min(int(minute_match.group(1)), 1440))
                    except ValueError:
                        minutes = 60
                args.append("upcoming")
                args.append(str(minutes))
            elif any(word in lowered for word in ["검색", "찾", "search", "find", "query"]):
                args.append("search")
                stop_words = ["일정", "검색", "찾아", "알려", "줘", "search", "find", "캘린더", "calendar"]
                tokens = [token for token in re.split(r"\s+", original) if token]
                filtered_tokens = [token for token in tokens if not any(stop in token.lower() for stop in stop_words)]
                query = " ".join(filtered_tokens).strip() or original.strip()
                args.append(query)
            else:
                if "미래" in lowered or "앞으로" in lowered or "soon" in lowered:
                    args.append("upcoming")
                    args.append("60")
                elif all(keyword not in lowered for keyword in ["today", "오늘"]):
                    args.append("today")
            return {"command": "calendar", "args": args}
    return None


def detect_drive_command(lowered: str, compact: str) -> Optional[Dict[str, Any]]:
    if any(keyword in lowered for keyword in DRIVE_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, DRIVE_REQUEST_VERBS):
            if any(word in lowered for word in ["도움", "help", "가이드", "사용법"]):
                return {"command": "drive_help"}
            if any(word in lowered for word in ["새", "신규", "recent", "업로드", "올라온", "추가", "동기화", "sync"]):
                return {"command": "drive_sync"}
            return {"command": "drive_list"}
    return None


def detect_settings_commands(lowered: str, compact: str, original: str) -> Optional[Dict[str, Any]]:
    if any(keyword in lowered for keyword in SETTINGS_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, SETTINGS_REQUEST_VERBS):
            return {"command": "settings"}
    if any(keyword in lowered for keyword in SETTINGS_UNDO_KEYWORDS):
        return {"command": "settings_undo"}
    intent = parse_preference_intent(original)
    if intent:
        return {"command": "settings_update", "preferences": intent}
    return None


def detect_integration_toggle(lowered: str) -> Optional[Dict[str, Any]]:
    for integration, keywords in INTEGRATION_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            if any(word in lowered for word in DISABLE_KEYWORDS):
                return {"command": "integration_toggle", "integration": integration, "state": False}
            if any(word in lowered for word in ENABLE_KEYWORDS):
                return {"command": "integration_toggle", "integration": integration, "state": True}
    return None


def detect_notion_command(lowered: str, original: str) -> Optional[Dict[str, Any]]:
    if any(keyword in lowered for keyword in NOTION_REQUEST_KEYWORDS):
        return {"command": "notion_log", "text": original}
    return None


def detect_natural_command(text: str) -> Optional[Dict[str, Any]]:
    lowered = text.lower()
    compact = lowered.replace(" ", "")

    for detector in (
        detect_gmail_command,
        detect_calendar_command,
    ):
        result = detector(lowered, compact, text)
        if result:
            return result

    result = detect_drive_command(lowered, compact)
    if result:
        return result

    if any(keyword in lowered for keyword in REMINDER_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, REMINDER_REQUEST_VERBS):
            return {"command": "reminder"}

    result = detect_settings_commands(lowered, compact, text)
    if result:
        return result

    if any(keyword in lowered for keyword in BOTS_KEYWORDS):
        if _contains_intent_phrase(lowered, compact, BOTS_REQUEST_VERBS):
            return {"command": "bots"}

    result = detect_integration_toggle(lowered)
    if result:
        return result

    result = detect_notion_command(lowered, text)
    if result:
        return result

    return None


def infer_task_type_from_text(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    for task_type, keywords in TASK_TYPE_KEYWORDS.items():
        if _match_any(normalized, [keyword.lower() for keyword in keywords]):
            return task_type
    return None


def infer_action_from_text(task_type: str, text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    actions = ACTION_KEYWORDS.get(task_type, {})
    for action_code, keywords in actions.items():
        if _match_any(normalized, [keyword.lower() for keyword in keywords]):
            return action_code
    return None


def infer_mode_from_text(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    for mode, keywords in MODE_KEYWORDS.items():
        if _match_any(normalized, [keyword.lower() for keyword in keywords]):
            return mode
    return None


def infer_pipeline_from_text(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    pipeline_keywords = {
        "full": ["모두", "전체", "풀", "full", "원본과"],
        "summary": ["요약", "summary", "간단", "텍스트만"],
        "original": ["원본만", "원본", "original"],
    }
    for preset, keywords in pipeline_keywords.items():
        if _match_any(normalized, [keyword.lower() for keyword in keywords]):
            return preset
    return None


def parse_preference_intent(text: str) -> Optional[Dict[str, Any]]:
    normalized = _normalize_text(text)
    triggers = ["앞으로", "항상", "기본", "default", "설정", "자동", "pipeline", "파이프라인"]
    for keywords in INTEGRATION_KEYWORDS.values():
        triggers.extend(keywords)
    if not _match_any(normalized, triggers):
        return None

    intent: Dict[str, Any] = {}

    mode = infer_mode_from_text(text)
    if mode:
        intent["mode"] = mode

    pipeline = infer_pipeline_from_text(text)
    if pipeline:
        intent["pipeline"] = pipeline

    task_type = infer_task_type_from_text(text)
    action = None

    if task_type:
        action = infer_action_from_text(task_type, text)
    else:
        for candidate_type in TASK_TYPE_KEYWORDS:
            candidate_action = infer_action_from_text(candidate_type, text)
            if candidate_action and candidate_action != "none":
                task_type = candidate_type
                action = candidate_action
                break

    if task_type and action:
        intent.setdefault("actions", {})[task_type] = action
    elif task_type and "pipeline" in intent:
        preset_actions = PIPELINE_PRESETS.get(intent["pipeline"], {})
        if preset_actions:
            intent.setdefault("actions", {})[task_type] = preset_actions.get(task_type)

    integration_changes: Dict[str, bool] = {}
    for integration, keywords in INTEGRATION_KEYWORDS.items():
        if _match_any(normalized, [keyword.lower() for keyword in keywords]):
            if _match_any(normalized, ENABLE_KEYWORDS):
                integration_changes[integration] = True
            elif _match_any(normalized, DISABLE_KEYWORDS):
                integration_changes[integration] = False

    if integration_changes:
        intent["integrations"] = integration_changes

    if not intent:
        return None

    return intent
