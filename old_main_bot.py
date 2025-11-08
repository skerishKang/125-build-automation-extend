#!/usr/bin/env python3
"""
Main Bot - Task Distribution & User Interaction
Role: User conversation, command handling, task distribution to specialized bots
"""
import os
import sys
import json
import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Tuple
from uuid import uuid4
import zoneinfo
from types import SimpleNamespace
import contextlib
from email.utils import parsedate_to_datetime

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext,
    filters,
)

from bots.shared.redis_utils import BotMessenger, REDIS_ENABLED  # type: ignore
from bots.shared.gemini_client import GeminiAnalyzer  # type: ignore
from bots.shared.user_preferences import preference_store, DEFAULT_PREFERENCES  # type: ignore
from bots.main_bot.action_handlers import (  # type: ignore
    execute_followup_action,
    ACTION_LABELS,
    FOLLOWUP_ACTIONS,
)
from bots.shared.telegram_utils import (  # type: ignore
    is_text_file,
    is_document_file,
    is_audio_file,
)
from backend.services.gmail import GmailService  # type: ignore
from backend.services import calendar_service  # type: ignore
from backend.services import notion  # type: ignore
from backend.services.drive_sync import (  # type: ignore
    get_folder_files,
    format_file_list,
    check_new_files,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main_bot")

# Configuration
MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_MAIN")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


def estimate_processing_time(task_type: str, file_info: Dict) -> int:
    """Estimate processing time in seconds based on task type and file info."""
    if task_type == "audio":
        duration = file_info.get("duration", 60)
        return int(duration * 2.5) + 30

    if task_type == "document":
        file_name = (file_info.get("file_name") or "").lower()
        file_size = file_info.get("file_size", 0)

        if file_name.endswith(".pdf"):
            estimated_pages = (file_size / 1024 / 1024) * 20
            return int(estimated_pages * 1.5) + 30
        if file_name.endswith(".docx"):
            return 60
        if file_name.endswith(".txt"):
            return 30
        if file_name.endswith(".xlsx") or file_name.endswith(".csv"):
            return 90
        return 60

    if task_type == "image":
        return 30

    return 60


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}초"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if remaining_seconds > 0:
        return f"{minutes}분 {remaining_seconds}초"
    return f"{minutes}분"


def split_into_chunks(text: str, limit: int = 3500) -> List[str]:
    """Split long strings into Telegram-friendly chunks."""
    if not text:
        return []
    return [text[i:i + limit] for i in range(0, len(text), limit)]


markdown_heading_pattern = re.compile(r"^#{1,6}\s*", flags=re.MULTILINE)
bold_pattern = re.compile(r"(\*\*|__)(.*?)\1")
inline_code_pattern = re.compile(r"`(.+?)`")

GMAIL_KEYWORDS = ["gmail", "메일", "이메일", "mail", "편지", "email"]
CALENDAR_KEYWORDS = ["일정", "schedule", "calendar", "캘린더", "약속", "meeting", "회의", "모임", "event"]
CALENDAR_ADD_KEYWORDS = ["등록", "추가", "잡아", "잡아줘", "만들어", "넣어", "일정잡아", "일정잡아줘", "등록해", "등록해줘", "추가해", "추가해줘", "예약해줘", "일정만들어"]
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
SETTINGS_KEYWORDS = [
    "설정",
    "preferences",
    "환경설정",
    "세팅",
]
BOTS_KEYWORDS = [
    "전문봇",
    "봇 목록",
    "봇상태",
    "bot status",
    "bots",
]
SETTINGS_UNDO_KEYWORDS = [
    "되돌려",
    "원래",
    "undo",
    "취소",
    "revert",
]
NOTION_REQUEST_KEYWORDS = [
    "노션",
    "notion",
    "기록해",
    "페이지",
]
INTEGRATION_KEYWORDS = {
    "slack": ["슬랙", "slack"],
    "notion": ["노션", "notion"],
}
ENABLE_KEYWORDS = ["켜", "켜줘", "활성", "on", "enable", "사용", "켜라"]
DISABLE_KEYWORDS = ["꺼", "끄", "비활성", "off", "disable", "중지", "멈춰"]

GMAIL_REQUEST_VERBS = [
    "해줘",
    "해주세요",
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

REMINDER_REQUEST_VERBS = [
    "해줘",
    "해주세요",
    "알려줘",
    "알려주세요",
    "보내줘",
    "보내주세요",
    "설정",
    "set",
    "remind",
]
SETTINGS_REQUEST_VERBS = [
    "열어줘",
    "열어",
    "보여줘",
    "보여",
    "설정",
    "manage",
]
BOTS_REQUEST_VERBS = [
    "알려줘",
    "보여줘",
    "확인",
    "status",
]


def _contains_intent_phrase(lowered: str, compact: str, phrases: List[str]) -> bool:
    for phrase in phrases:
        phrase_lower = phrase.lower()
        if phrase_lower in lowered or phrase_lower in compact:
            return True
    return False


def simplify_markdown(text: str) -> str:
    """Convert basic Markdown into cleaner plain text for Telegram."""
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n")
    cleaned = markdown_heading_pattern.sub("", cleaned)
    cleaned = bold_pattern.sub(r"\2", cleaned)
    cleaned = inline_code_pattern.sub(r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = cleaned.replace("* ", "- ").replace("- ", "- ")
    cleaned = cleaned.replace("\t", "    ")
    return cleaned.strip()


def format_email_entry(email: Dict[str, Any], index: int) -> str:
    """Create a human-friendly summary of a single email."""
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


def parse_relative_date_time(text: str, reference: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Parse natural language Korean date/time expressions."""
    reference = reference or datetime.now().astimezone()
    date = None
    time_hour = None
    time_minute = 0
    duration_minutes = 60

    lowered = text.lower()

    if "모레" in lowered:
        date = (reference + timedelta(days=2)).date()
    elif "내일모레" in lowered or "글피" in lowered:
        date = (reference + timedelta(days=3)).date()
    elif "내일" in lowered:
        date = (reference + timedelta(days=1)).date()
    elif "오늘" in lowered:
        date = reference.date()

    month_day_match = re.search(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일', text)
    if month_day_match:
        month = int(month_day_match.group(1))
        day = int(month_day_match.group(2))
        year = reference.year
        if month < reference.month or (month == reference.month and day < reference.day):
            year += 1
        date = datetime(year, month, day).date()

    date_match_alt = re.search(r'(\d{1,2})/(\d{1,2})', text)
    if date_match_alt and not month_day_match:
        month = int(date_match_alt.group(1))
        day = int(date_match_alt.group(2))
        year = reference.year
        if month < reference.month or (month == reference.month and day < reference.day):
            year += 1
        date = datetime(year, month, day).date()

    if date is None:
        date = reference.date()

    meridiem_offset = 0
    if any(token in lowered for token in ["오후", "저녁", "밤", "pm"]):
        meridiem_offset = 12
    if any(token in lowered for token in ["오전", "아침", "새벽", "am"]):
        meridiem_offset = 0

    time_match = re.search(r'(\d{1,2})\s*시\s*(\d{1,2})?\s*분?', text)
    if time_match:
        time_hour = int(time_match.group(1))
        minutes = time_match.group(2)
        time_minute = int(minutes) if minutes else 0
    else:
        colon_match = re.search(r'(\d{1,2}):(\d{2})', text)
        if colon_match:
            time_hour = int(colon_match.group(1))
            time_minute = int(colon_match.group(2))

    if time_hour is None:
        time_hour = 9

    if meridiem_offset == 12 and time_hour < 12:
        time_hour += 12
    if meridiem_offset == 0 and time_hour == 12 and "오전" in lowered:
        time_hour = 0

    duration_match_hours = re.search(r'(\d{1,2})\s*시간', text)
    duration_match_minutes = re.search(r'(\d{1,2})\s*분', text)
    if duration_match_hours:
        try:
            duration_minutes = int(duration_match_hours.group(1)) * 60
        except ValueError:
            pass
    if duration_match_minutes:
        try:
            duration_minutes = max(duration_minutes, int(duration_match_minutes.group(1)))
        except ValueError:
            pass

    start_dt = datetime.combine(date, datetime.min.time()).replace(
        hour=time_hour,
        minute=time_minute,
        tzinfo=zoneinfo.ZoneInfo('Asia/Seoul'),
    )

    # Heuristic for AM/PM if not explicitly specified
    # If no meridiem (AM/PM) is specified and the parsed hour is less than 12,
    # and the current hour is already past the parsed hour, assume PM.
    if meridiem_offset == 0 and time_hour < 12:
        if reference.hour >= time_hour:
            start_dt = start_dt + timedelta(hours=12)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    return {
        "start": start_dt,
        "end": end_dt,
        "duration_minutes": duration_minutes,
    }


last_preference_states: Dict[str, Dict[str, Any]] = {}


def extract_event_title(original_text: str) -> str:
    removal_patterns = [
        r'(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(에|에서|부터|까지)?',
        r'(\d{1,2})/(\d{1,2})\s*(에|에서|부터|까지)?',
        r'(\d{1,2})\s*시\s*(\d{0,2})?\s*분?\s*(에|에서|부터|까지)?',
        r'(\d{1,2}):(\d{2})\s*(에|에서|부터|까지)?',
    ]
    removal_words = [
        "등록해줘", "등록해", "추가해줘", "추가해", "잡아줘", "잡아", "예약해줘", "예약해",
        "해주세요", "해줘", "해줄래", "부탁", "달력", "캘린더", "등록", "추가", "만들어",
        "오늘", "내일", "모레", "다가오는", "곧", "이번주", "이번 주", "week", "today", "tomorrow",
        "오전", "오후", "저녁", "밤", "새벽",
    ]

    text = original_text
    for pattern in removal_patterns:
        text = re.sub(pattern, " ", text)
    for word in removal_words:
        text = text.replace(word, " ")

    summary = re.sub(r'\s+', ' ', text).strip()
    if not summary:
        summary = "일정"
    return summary


def detect_natural_command(text: str) -> Optional[Dict[str, Any]]:
    """Detect natural language intents for Gmail or Calendar commands."""
    lowered = text.lower()
    compact = lowered.replace(" ", "")

    if any(keyword in lowered for keyword in GMAIL_KEYWORDS):
        if "/gmail" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, GMAIL_REQUEST_VERBS)
        if not has_intent:
            return None

        args: List[str] = []
        count = None

        # Korean number mapping
        korean_numbers = {
            "하나": 1, "일": 1, "두개": 2, "둘": 2, "이": 2,
            "세개": 3, "셋": 3, "삼": 3, "네개": 4, "넷": 4, "사": 4,
            "다섯개": 5, "다섯": 5, "오": 5, "여섯개": 6, "여섯": 6, "육": 6,
            "일곱개": 7, "일곱": 7, "칠": 7, "여덟개": 8, "여덟": 8, "팔": 8,
            "아홉개": 9, "아홉": 9, "구": 9, "열개": 10, "열": 10, "십": 10
        }

        # Check for Korean numbers
        for korean_num in korean_numbers:
            if korean_num in lowered:
                count = korean_numbers[korean_num]
                break

        # Check for Arabic numbers
        if not count:
            count_match = re.search(r'(\d{1,2})\s*(개|건|통|mail|mails|message|messages)?', lowered)
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

    if any(keyword in lowered for keyword in CALENDAR_ADD_KEYWORDS) and any(keyword in lowered for keyword in CALENDAR_KEYWORDS + ["일정", "모임", "회의"]):
        if "/calendar" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, CALENDAR_REQUEST_VERBS)
        if not has_intent:
            return None

        parsed = parse_relative_date_time(text)
        if not parsed:
            return None
        summary = extract_event_title(text)
        event_info = {
            "summary": summary,
            "start": parsed["start"],
            "end": parsed["end"],
            "duration_minutes": parsed["duration_minutes"],
        }
        return {"command": "calendar_add", "event_info": event_info}

    if any(keyword in lowered for keyword in CALENDAR_KEYWORDS):
        if "/calendar" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, CALENDAR_REQUEST_VERBS)
        if not has_intent:
            return None

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
            minute_match = re.search(r'(\d{1,3})\s*(분|min|minute|minutes)', lowered)
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
            tokens = [token for token in re.split(r'\s+', text) if token]
            filtered_tokens = [token for token in tokens if not any(stop in token.lower() for stop in stop_words)]
            query = " ".join(filtered_tokens).strip()
            if not query:
                query = text.strip()
            args.append(query)
        else:
            if "미래" in lowered or "앞으로" in lowered or "soon" in lowered:
                args.append("upcoming")
                args.append("60")
            elif all(keyword not in lowered for keyword in ["today", "오늘"]):
                args.append("today")

        return {"command": "calendar", "args": args}

    if any(keyword in lowered for keyword in DRIVE_KEYWORDS):
        if "/drive" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, DRIVE_REQUEST_VERBS)
        if not has_intent:
            return None

        if any(word in lowered for word in ["도움", "help", "가이드", "사용법"]):
            return {"command": "drive_help"}

        if any(word in lowered for word in ["새", "신규", "recent", "업로드", "올라온", "추가", "동기화", "sync"]):
            return {"command": "drive_sync"}

        return {"command": "drive_list"}

    if any(keyword in lowered for keyword in REMINDER_KEYWORDS):
        if "/remind" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, REMINDER_REQUEST_VERBS)
        if not has_intent:
            return None

        return {"command": "reminder"}

    if any(keyword in lowered for keyword in SETTINGS_KEYWORDS):
        if "/settings" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, SETTINGS_REQUEST_VERBS)
        if not has_intent:
            return None

        return {"command": "settings"}

    if any(keyword in lowered for keyword in BOTS_KEYWORDS):
        if "/bots" in lowered:
            return None

        has_intent = _contains_intent_phrase(lowered, compact, BOTS_REQUEST_VERBS)
        if not has_intent:
            return None

        return {"command": "bots"}

    if any(keyword in lowered for keyword in SETTINGS_UNDO_KEYWORDS):
        return {"command": "settings_undo"}

    if any(keyword in lowered for keyword in NOTION_REQUEST_KEYWORDS):
        return {"command": "notion_log", "text": text}

    preference_intent = parse_preference_intent(text)
    if preference_intent:
        return {"command": "settings_update", "preferences": preference_intent}

    return None


async def send_progress_updates(
    bot: Bot,
    chat_id: int,
    task_id: str,
    task_type: str,
    estimated_time: int,
    cancel_event: asyncio.Event,
) -> None:
    """Send progress updates until the task completes."""
    emoji_map = {"audio": "🎤", "document": "📄", "image": "🖼️"}
    emoji = emoji_map.get(task_type, "⚙️")

    loop = asyncio.get_event_loop()
    start_time = loop.time()
    update_interval = 20
    last_percent = -1

    await bot.send_message(
        chat_id=chat_id,
        text=f"{emoji} 처리 시작! ⏱️ 예상 시간: ~{format_duration(estimated_time)}",
    )

    while not cancel_event.is_set():
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=update_interval)
            break
        except asyncio.TimeoutError:
            elapsed = int(loop.time() - start_time)
            if estimated_time > 0:
                progress_percent = min(99, int((elapsed / estimated_time) * 100))
                if progress_percent > 0:
                    remaining = int((estimated_time * (100 - progress_percent)) / progress_percent)
                else:
                    remaining = estimated_time
            else:
                progress_percent = 50
                remaining = 0

            if progress_percent == last_percent:
                continue

            last_percent = progress_percent

            filled = int(progress_percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_text = (
                f"{emoji} 처리 중... {progress_percent}%\n"
                f"{bar}\n"
                f"⏱️ 경과: {format_duration(elapsed)}"
            )
            if remaining > 0:
                progress_text += f" / 남은 시간: ~{format_duration(remaining)}"

            try:
                await bot.send_message(chat_id=chat_id, text=progress_text)
            except Exception as exc:
                logger.warning("Failed to update progress message: %s", exc)

    total_elapsed = int(loop.time() - start_time)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"{emoji} 처리 완료! ⏱️ 총 경과: {format_duration(total_elapsed)}",
        )
    except Exception as exc:
        logger.warning("Failed to finalize progress message: %s", exc)

# Global state
active_tasks: Dict[str, Dict[str, Dict[str, Any]]] = {}  # chat_id -> task_id -> task_info
user_sessions: Dict[str, Dict] = {}  # user_id -> session_info
pending_results: Dict[str, Dict[str, Any]] = {}  # task_id -> {event, result}
followup_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> follow-up context
preference_history: Dict[str, List[Dict[str, Any]]] = {}

PIPELINE_PRESET_LABELS = {
    "full": "원본+요약 모두 저장",
    "summary": "요약 결과만 저장",
    "original": "원본 파일만 저장",
}
manual_result_listener_task: Dict[str, Optional[asyncio.Task]] = {"task": None}

MODE_LABELS = {
    "ask": "대화형 모드 (항상 물어보기)",
    "auto": "자동 실행 모드",
    "skip": "요약만 받고 건너뛰기",
}


def get_default_action_for_type(prefs: Dict[str, Any], task_type: str) -> str:
    defaults = prefs.get("default_actions", {})
    if isinstance(defaults, dict):
        return defaults.get(task_type, "none")
    return "none"


def build_default_actions_summary(prefs: Dict[str, Any]) -> Dict[str, str]:
    return {
        task_type: get_default_action_for_type(prefs, task_type)
        for task_type in ("document", "image", "audio")
    }


def set_default_action_for_type(chat_id: str, task_type: str, action: str) -> Dict[str, Any]:
    prefs = preference_store.get_preferences(chat_id)
    defaults = build_default_actions_summary(prefs)
    defaults[task_type] = action
    return preference_store.set_preferences(chat_id, {"default_actions": defaults})


def format_action_label(action_code: str) -> str:
    return ACTION_LABELS.get(action_code, "(설정 없음)")


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


def _normalize_text(text: str) -> str:
    return re.sub(r"[\s]+", " ", text.lower()).strip()


def _match_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


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
        # If no specific task type, but mentions summary/original keywords, apply pipeline
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


def build_settings_message(prefs: Dict[str, Any]) -> str:
    """Create user-facing summary of current automation preferences."""
    mode_label = MODE_LABELS.get(prefs.get("mode", ""), "미설정")
    defaults = build_default_actions_summary(prefs)
    integrations = prefs.get("integrations", {})
    slack_state = "✅" if integrations.get("slack", True) else "❌"
    notion_state = "✅" if integrations.get("notion", False) else "❌"

    lines = [
        "⚙️ 현재 하이브리드 자동화 설정",
        f"- 기본 모드: {mode_label}",
        "",
        f"문서 자동 작업: {format_action_label(defaults['document'])}",
        "  └ 문서 업로드 후 어떤 후속 작업을 기본 적용할지 선택합니다.",
        f"이미지 자동 작업: {format_action_label(defaults['image'])}",
        "  └ 이미지 업로드 시 OCR/요약/저장 등 기본 동작을 설정합니다.",
        f"오디오 자동 작업: {format_action_label(defaults['audio'])}",
        "  └ 음성 메시지 처리 후 자동으로 실행할 후속 액션을 지정합니다.",
        "",
        "🚀 파이프라인 프리셋",
        f"- 풀: {PIPELINE_PRESET_LABELS['full']} (원본 업로드 + 요약 + 노션/슬랙)",
        f"- 요약: {PIPELINE_PRESET_LABELS['summary']} (요약 위주, 원본 제외)",
        f"- 원본: {PIPELINE_PRESET_LABELS['original']} (파일 보존, 요약 생략)",
        "",
        "🔗 통합 설정",
        f"- Slack 알림: {slack_state} (파일 처리 결과를 Slack에도 발송)",
        f"- Notion 기록: {notion_state} (요약·추출 결과를 자동 기록)",
        "",
        "아래 인라인 버튼으로 모드·자동 작업·통합 설정을 즉시 변경할 수 있어요.",
    ]
    return "\n".join(lines)


def get_actions_for_type(task_type: str) -> Dict[str, Dict[str, Any]]:
    return {
        code: data
        for code, data in FOLLOWUP_ACTIONS.items()
        if data.get("task_type") == task_type
    }


def build_settings_keyboard(prefs: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Return inline keyboard for settings adjustments."""
    rows = [
        [
            InlineKeyboardButton("대화형 모드", callback_data="pref_mode|ask"),
            InlineKeyboardButton("자동 실행", callback_data="pref_mode|auto"),
            InlineKeyboardButton("요약만", callback_data="pref_mode|skip"),
        ]
    ]

    for task_type in ("document", "image", "audio"):
        actions = get_actions_for_type(task_type)
        buttons = [
            InlineKeyboardButton(
                f"{TASK_TYPE_LABELS[task_type]}·{info['label_once']}",
                callback_data=f"pref_action|{task_type}|{code}",
            )
            for code, info in actions.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                f"{TASK_TYPE_LABELS[task_type]}·없음",
                callback_data=f"pref_action|{task_type}|none",
            )
        )
        rows.append(buttons)

    preset_buttons = [
        InlineKeyboardButton("풀 파이프라인", callback_data="pref_pipeline|full"),
        InlineKeyboardButton("요약 파이프라인", callback_data="pref_pipeline|summary"),
        InlineKeyboardButton("원본 파이프라인", callback_data="pref_pipeline|original"),
    ]
    rows.append(preset_buttons)
    integrations = prefs.get("integrations", {})
    slack_label = "Slack 알림 ON" if integrations.get("slack", True) else "Slack 알림 OFF"
    notion_label = "Notion 기록 ON" if integrations.get("notion", False) else "Notion 기록 OFF"
    rows.append([
        InlineKeyboardButton(slack_label, callback_data="pref_integration|slack|toggle"),
        InlineKeyboardButton(notion_label, callback_data="pref_integration|notion|toggle"),
    ])
    rows.append([
        InlineKeyboardButton("되돌리기", callback_data="pref_undo|"),
    ])

    return InlineKeyboardMarkup(rows)


def build_followup_keyboard(task_type: str, task_id: str) -> InlineKeyboardMarkup:
    actions = get_actions_for_type(task_type)

    once_row = [
        InlineKeyboardButton(info["label_once"], callback_data=f"follow|{task_id}|once|{code}")
        for code, info in actions.items()
    ]
    auto_row = [
        InlineKeyboardButton(info["label_auto"], callback_data=f"follow|{task_id}|auto|{code}")
        for code, info in actions.items()
    ]
    extra_row = [
        InlineKeyboardButton("건너뛰기", callback_data=f"follow|{task_id}|once|none"),
        InlineKeyboardButton("항상 건너뛰기", callback_data=f"follow|{task_id}|skip|none"),
        InlineKeyboardButton("설정 열기", callback_data="pref_open|global"),
    ]

    preset_row = [
        InlineKeyboardButton("풀 파이프라인", callback_data="pref_pipeline|full"),
        InlineKeyboardButton("요약 파이프라인", callback_data="pref_pipeline|summary"),
        InlineKeyboardButton("원본 파이프라인", callback_data="pref_pipeline|original"),
    ]

    rows = [once_row, auto_row, preset_row, extra_row]
    return InlineKeyboardMarkup(rows)


async def prompt_followup(bot: Bot, chat_id: str, task_id: str, task_type: str) -> None:
    message = FOLLOWUP_PROMPTS.get(task_type, "후속 작업을 선택해주세요.")
    prefs = preference_store.get_preferences(chat_id)
    defaults = build_default_actions_summary(prefs)
    mode_label = MODE_LABELS.get(prefs.get("mode", ""), "미설정")
    current_default = format_action_label(defaults.get(task_type, "none"))
    message = (
        f"{message}\n\n"
        f"현재 모드: {mode_label}\n"
        f"기본 {TASK_TYPE_LABELS.get(task_type, '')} 작업: {current_default}"
    )

    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=message,
            reply_markup=build_followup_keyboard(task_type, task_id),
        )
    except Exception as exc:
        logger.error("Failed to send follow-up prompt: %s", exc)


def register_followup_task(task_id: str, chat_id: str, task_type: str, result: Dict[str, Any], meta: Dict[str, Any]) -> None:
    followup_tasks[task_id] = {
        "chat_id": chat_id,
        "task_type": task_type,
        "result": result,
        "meta": meta,
    }


async def apply_preferences_to_task(bot: Bot, chat_id: str, task_id: str, task_type: str, prefs: Dict[str, Any]) -> None:
    record = followup_tasks.get(task_id)
    if not record:
        return

    task_type = task_type or record.get("task_type", "document")

    mode = prefs.get("mode", DEFAULT_PREFERENCES["mode"])
    action = get_default_action_for_type(prefs, task_type)

    if mode == "auto" and action != "none":
        action_label = format_action_label(action)
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"🔁 자동 실행 설정에 따라 \"{action_label}\" 작업을 진행합니다.",
            )
        except Exception as exc:
            logger.error("Failed to announce auto action (settings): %s", exc)
        await execute_followup_action(action, bot, chat_id, record)
        followup_tasks.pop(task_id, None)
    elif mode == "skip":
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text="결과만 전달하고 후속 작업은 건너뛰겠습니다.",
            )
        except Exception as exc:
            logger.error("Failed to send skip confirmation: %s", exc)
        followup_tasks.pop(task_id, None)
    else:
        await prompt_followup(bot, chat_id, task_id, task_type)


async def apply_preferences_to_pending_tasks(bot: Bot, chat_id: str, task_type: Optional[str], prefs: Dict[str, Any]) -> None:
    for task_id, record in list(followup_tasks.items()):
        if record.get("chat_id") != chat_id:
            continue
        if task_type and record.get("task_type") != task_type:
            continue
        await apply_preferences_to_task(bot, chat_id, task_id, record.get("task_type"), prefs)


async def manual_result_listener(bot: Bot) -> None:
    """Fallback loop to poll Redis results when JobQueue is unavailable."""
    dummy_context = SimpleNamespace(bot=bot)
    while True:
        await poll_result_messages(dummy_context)
        await asyncio.sleep(1.0)


# Constants for preference history
PREFERENCE_HISTORY_LIMIT = 5


async def handle_settings_update(update: Update, context: ContextTypes.DEFAULT_TYPE, intent: Dict[str, Any]) -> None:
    chat_id = str(update.effective_chat.id)
    previous = preference_store.get_preferences(chat_id)
    preference_history.setdefault(chat_id, []).append(previous)
    preference_history[chat_id] = preference_history[chat_id][-PREFERENCE_HISTORY_LIMIT:]

    updates: Dict[str, Any] = {}
    mode = intent.get("mode")
    if mode:
        updates["mode"] = mode

    actions = intent.get("actions")
    if actions:
        defaults = build_default_actions_summary(previous)
        defaults.update(actions)
        updates["default_actions"] = defaults

    pipeline = intent.get("pipeline")
    if pipeline:
        preset = PIPELINE_PRESETS.get(pipeline, {})
        if preset:
            defaults = build_default_actions_summary(previous)
            defaults.update(preset)
            updates.setdefault("default_actions", defaults)
            updates.setdefault("mode", previous.get("mode", "auto"))

    integrations = intent.get("integrations")
    if integrations:
        current_integrations = previous.get("integrations", {}).copy()
        current_integrations.update(integrations)
        updates["integrations"] = current_integrations

    if not updates:
        await update.message.reply_text("⚠️ 적용할 설정을 찾지 못했어요.")
        return

    preference_store.set_preferences(chat_id, updates)
    prefs = preference_store.get_preferences(chat_id)

    summary_lines = ["✅ 설정이 업데이트되었습니다!", f"- 모드: {MODE_LABELS.get(prefs.get('mode', ''), '미설정')}" ]

    defaults = build_default_actions_summary(prefs)
    summary_lines.append("- 기본 작업 요약:")
    summary_lines.append(f"  - 문서: {format_action_label(defaults['document'])}")
    summary_lines.append(f"  - 이미지: {format_action_label(defaults['image'])}")
    summary_lines.append(f"  - 오디오: {format_action_label(defaults['audio'])}")

    if pipeline:
        summary_lines.append(f"- 파이프라인: {PIPELINE_PRESET_LABELS.get(pipeline, pipeline)}")

    if integrations:
        for name, state in integrations.items():
            label = "ON" if state else "OFF"
            summary_lines.append(f"- {name.title()} 통합: {label}")

    await update.message.reply_text("\n".join(summary_lines))

    await update.message.reply_text(
        build_settings_message(prefs),
        reply_markup=build_settings_keyboard(prefs),
    )

    for task_id, record in list(followup_tasks.items()):
        if record.get("chat_id") == chat_id:
            await apply_preferences_to_task(context.bot, chat_id, task_id, record.get("task_type"), prefs)


async def handle_settings_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    history = preference_history.get(chat_id, [])
    if not history:
        await update.message.reply_text("되돌릴 설정이 없습니다.")
        return

    previous = history.pop()
    preference_store.set_preferences(chat_id, previous)
    prefs = preference_store.get_preferences(chat_id)
    await update.message.reply_text("↩️ 설정을 이전 상태로 되돌렸어요.")
    await update.message.reply_text(
        build_settings_message(prefs),
        reply_markup=build_settings_keyboard(prefs),
    )


async def handle_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bots command - Check specialized bot status"""
    status_text = """
전문봇 상태 요약

📄 문서봇
- 역할: PDF, DOCX, TXT, CSV 등을 전문 분석
- 기능: 텍스트 추출 → Gemini 요약 → 후속 액션 버튼 제공
- 권장 사용: 회의록/보고서 업로드 후 노션 기록·슬랙 알림 자동화

🎧 오디오봇
- 역할: OGG, MP3, WAV 등 음성 메시지 처리
- 기능: 길이별로 Gemini 멀티모달 or Whisper+Gemini 조합 활용
- 권장 사용: 음성 메모 → 텍스트 요약 → 리마인더/Drive 업로드 연계

🖼️ 사진봇
- 역할: JPG, PNG 등 이미지 분석 및 OCR 처리
- 기능: 이미지 설명, 텍스트 추출, 후속 태스크 추천
- 권장 사용: 화이트보드 사진 → 텍스트 추출 → Notion 기록

사용 방법: 메인봇 대화창에 파일을 업로드하면 자동으로 적절한 전문봇이 실행되고, 후속 작업 버튼이 함께 제공됩니다.
"""

    await update.message.reply_text(status_text)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    name = user.first_name or "사용자"
    chat_id = update.effective_chat.id

    welcome_message = f"""
안녕하세요 {name}님! 👋 메인봇입니다.

📌 핵심 기능
- 자유 대화 & 요약 (Gemini 2.5 Flash-Lite)
- 문서/이미지/음성 업로드 자동 분석
- Gmail·캘린더·Drive 모니터링 및 연동
- Slack/Notion 통합 기록

⚙️ 추천 단계
1) /settings 로 기본 자동화와 통합 여부를 설정하세요.
2) /bots 로 전문봇 상태와 역할을 확인하세요.
3) /status 로 Redis, Gemini 등 런타임 상태를 점검하세요.

💡 사용 팁
- "메일 좀 보여줘", "내일 일정 잡아줘" 같은 자연어 명령도 인식합니다.
- 파일 업로드 후 메시지로 후속 액션 버튼이 제공됩니다.
- `/help` 로 전체 명령어와 활용법을 확인할 수 있습니다.

언제든지 필요한 자동화를 말씀해 주세요!
    """

    await update.message.reply_text(welcome_message)
    logger.info(f"User {user.id} started the bot")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
도움말

일반 대화
- 텍스트를 입력하시면 Gemini AI가 답변합니다

문서 처리
- PDF, DOCX, TXT, CSV 파일 업로드
- 문서봇이 자동으로 분석합니다
- 진행 상황을 실시간으로 알려드려요

음성 처리
- OGG, MP3, WAV 파일 업로드
- 오디오봇이 음성을 텍스트로 변환하고 요약합니다

이미지 분석
- JPG, PNG 등 이미지 업로드
- 사진봇이 이미지를 분석하고 설명해드립니다

추가 명령어
- /status - 현재 봇 상태
- /bots - 전문봇 상태 확인
- /gmail [개수] [mark] - 읽지 않은 Gmail 확인 (mark 옵션 시 읽음 처리)
- /calendar [today|tomorrow|week|upcoming|search 키워드] - 구글 캘린더 일정 확인

사용 팁
- 여러 파일을 동시에 업로드 가능
- 파일 크기는 최대 50MB까지 지원
- 분석 중에도 다른 대화 계속 가능!
    """

    await update.message.reply_text(help_text)


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    chat_id = str(update.effective_chat.id)

    # Get task status
    task_count = sum(len(tasks) for tasks in active_tasks.values())
    active_task_info = ""

    chat_tasks = active_tasks.get(chat_id, {})
    if chat_tasks:
        lines = ["[STATS] 현재 작업:"]
        for idx, info in enumerate(chat_tasks.values(), 1):
            lines.extend([
                f"- #{idx} 타입: {info.get('type', 'N/A')}",
                f"  상태: {info.get('status', 'N/A')}",
                f"  시작: {info.get('start_time', 'N/A')}",
            ])
        active_task_info = "\n".join(lines)

    redis_status = "활성"
    if not REDIS_ENABLED:
        redis_status = "비활성 (환경 변수: REDIS_ENABLED=false)"
    else:
        try:
            messenger.redis_client.ping()  # type: ignore[attr-defined]
        except Exception:
            redis_status = "연결 실패"

    gemini_status = "활성" if GEMINI_API_KEY else "비활성"
    supabase_status = "활성" if SUPABASE_URL and SUPABASE_KEY else "미설정"

    status_text = f"""
메인봇 상태

연결 상태:
- 메인봇: 실행 중
- Redis: {REDIS_HOST}:{REDIS_PORT} ({redis_status})
- Gemini AI: {gemini_status}
- Supabase 메모리: {supabase_status}

작업 현황:
- 활성 작업: {task_count}개
{active_task_info}

전문봇:
- 문서봇: 준비 완료
- 오디오봇: 준비 완료
- 사진봇: 준비 완료
    """

    await update.message.reply_text(status_text)


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command for automation preferences."""
    chat_id = str(update.effective_chat.id)
    prefs = preference_store.get_preferences(chat_id)

    await update.message.reply_text(
        build_settings_message(prefs),
        reply_markup=build_settings_keyboard(prefs),
    )


async def handle_notion_log(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user

    title = f"대화 기록 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    content = text.strip()

    if len(content) > 2000:
        content = content[:2000] + "..."

    blocks = [
        notion.build_paragraph_block(f"채팅 ID: {chat_id}"),
        notion.build_paragraph_block(f"사용자: {user.full_name if user else '알 수 없음'}"),
        notion.build_paragraph_block(""),
        notion.build_paragraph_block(content),
    ]

    success = notion.create_page(title, blocks)
    if success:
        await update.message.reply_text("🗂️ 노션에 기록했어요!")
    else:
        await update.message.reply_text("⚠️ 노션에 기록하지 못했어요. 설정을 확인해주세요.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with Gemini AI"""
    text = (update.message.text or "").strip()

    if text.startswith('/'):
        return

    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    logger.info(f"Text message from user {user_id}: {text[:50]}...")

    if not GEMINI_API_KEY:
        await update.message.reply_text(
            "[WARN] Gemini API가 설정되지 않아 AI 대화가 비활성화되어 있어요."
        )
        return

    detected = detect_natural_command(text)
    if detected:
        command = detected.get("command")
        args = detected.get("args", [])

        if command == "gmail":
            await handle_gmail(update, context, args_override=args)
            return
        if command == "calendar":
            await handle_calendar(update, context, args_override=args)
            return
        if command == "calendar_add":
            await handle_calendar_add(update, context, detected["event_info"])
            return
        if command == "drive_help":
            await handle_drive_help(update, context)
            return
        if command == "drive_list":
            await handle_drive_list(update, context, args_override=args)
            return
        if command == "drive_sync":
            await handle_drive_sync(update, context)
            return
        if command == "reminder":
            await handle_reminder(update, context, original_text=text)
            return
        if command == "settings_update":
            await handle_settings_update(update, context, detected["preferences"])
            return
        if command == "settings_undo":
            await handle_settings_undo(update, context)
            return
        if command == "notion_log":
            await handle_notion_log(update, context, detected.get("text", text))
            return
        if command == "settings":
            await handle_settings(update, context)
            return
        if command == "bots":
            await handle_bots(update, context)
            return

    lowered = text.lower()

    # Detect natural language commands
    # Show usage help if keywords detected
    if "/gmail" in lowered:
        await update.message.reply_text(
            "메일을 확인하려면 `/gmail [개수] [mark]` 명령을 사용해주세요.",
            parse_mode="Markdown",
        )
        return

    if "/calendar" in lowered:
        await update.message.reply_text(
            "일정을 확인하려면 `/calendar [today|tomorrow|week|upcoming|search 키워드]` 명령을 사용해주세요.",
            parse_mode="Markdown",
        )
        return

    # Send typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Use Gemini to generate response (force Korean response)
    prompt = "다음 텍스트에 대한 답변을 한국어로 해주세요."
    response = gemini.analyze_text(prompt + "\n\n" + text)

    if response:
        # Split long messages
        if len(response) > 4000:
            # Send in chunks
            for i in range(0, len(response), 4000):
                chunk = response[i:i+4000]
                await update.message.reply_text(chunk)
                await asyncio.sleep(0.1)
        else:
            await update.message.reply_text(response)
    else:
        await update.message.reply_text(
            "[WARN] 죄송해요, 지금은 답변을 생성할 수 없어요."
        )


async def handle_gmail(update: Update, context: ContextTypes.DEFAULT_TYPE, args_override: Optional[List[str]] = None):
    """Handle /gmail command to fetch recent unread emails."""
    chat_id = update.effective_chat.id
    args = args_override if args_override is not None else (getattr(context, "args", []) or [])

    count = 3
    mark_as_read = False
    unread_only = True

    for arg in args:
        lowered = arg.lower()
        if lowered in {"mark", "read", "--mark-read", "-m", "markread"}:
            mark_as_read = True
        elif lowered in {"all", "--all"}:
            unread_only = False
        else:
            # Try to parse as number or Korean number
            try:
                # Korean number mapping
                korean_numbers = {
                    "하나": 1, "일": 1, "1": 1,
                    "둘": 2, "이": 2, "2": 2,
                    "셋": 3, "삼": 3, "3": 3,
                    "넷": 4, "사": 4, "4": 4,
                    "다섯": 5, "오": 5, "5": 5,
                    "여섯": 6, "육": 6, "6": 6,
                    "일곱": 7, "칠": 7, "7": 7,
                    "여덟": 8, "팔": 8, "8": 8,
                    "아홉": 9, "구": 9, "9": 9,
                    "열": 10, "십": 10, "10": 10
                }

                if lowered in korean_numbers:
                    count = korean_numbers[lowered]
                else:
                    count = max(1, min(int(arg), 10))
            except ValueError:
                continue

    status_text = f"📬 Gmail에서 최근 {'읽지 않은 ' if unread_only else ''}메일 {count}건을 확인하고 있습니다..."
    await update.message.reply_text(status_text)

    gmail_service = GmailService()

    def fetch_emails():
        try:
            if not gmail_service.authenticate():
                return False, "Gmail 인증에 실패했습니다. OAuth 또는 서비스 계정 설정을 확인해주세요.", []
            emails = gmail_service.fetch_email_details(
                max_results=count,
                mark_as_read=mark_as_read,
                unread_only=unread_only,
            )
            return True, "", emails
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Gmail fetch failed: %s", exc)
            return False, f"Gmail 정보를 가져오는 중 오류가 발생했습니다: {exc}", []

    success, error_message, emails = await asyncio.to_thread(fetch_emails)

    if not success:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ {error_message}")
        return

    if not emails and unread_only:
        await context.bot.send_message(chat_id=chat_id, text="읽지 않은 새로운 메일이 없습니다. 가장 최근 메일을 대신 보여드릴게요.")
        success, error_message, emails = await asyncio.to_thread(lambda: (
            True,
            "",
            gmail_service.fetch_email_details(
                max_results=count,
                mark_as_read=False,
                unread_only=False,
            )
        ))
        if not emails:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "최근 메일 정보를 찾을 수 없습니다. 연결된 Gmail 계정이 맞는지, "
                    "또는 OAuth 인증이 완료되었는지 확인해주세요."
                ),
            )
            return

    if not emails:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "최근 메일 정보를 찾을 수 없습니다. "
                "읽지 않은 메일이 없거나, 현재 연결된 계정에 접근 권한이 없을 수 있습니다."
            ),
        )
        return

    lines = [format_email_entry(email, idx) for idx, email in enumerate(emails, 1)]
    message = "\n\n".join(lines)
    await context.bot.send_message(chat_id=chat_id, text=message)

    if mark_as_read:
        await context.bot.send_message(chat_id=chat_id, text="✅ 표시한 메일은 읽음 처리했습니다.")


async def handle_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, args_override: Optional[List[str]] = None):
    """Handle /calendar command to show upcoming events."""
    chat_id = update.effective_chat.id
    args = args_override if args_override is not None else (getattr(context, "args", []) or [])

    if args and args[0].lower() == "add":
        parts = " ".join(args[1:]).split("|")
        parts = [part.strip() for part in parts if part.strip()]

        now = datetime.now().astimezone()
        summary = parts[0] if parts else "일정"
        date_part = parts[1] if len(parts) > 1 else now.strftime("%Y-%m-%d")
        time_part = parts[2] if len(parts) > 2 else "09:00"
        duration_part = parts[3] if len(parts) > 3 else "60"

        try:
            start_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            time_parts = time_part.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            start_dt = datetime.combine(start_date, datetime.min.time()).replace(
                hour=hour, minute=minute, tzinfo=now.tzinfo
            )
            duration_minutes = max(15, int(duration_part))
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ 올바른 형식이 아닙니다. 예: `/calendar add 회의 | 2025-11-07 | 15:00 | 90`",
            )
            return

        event_info = {
            "summary": summary,
            "start": start_dt,
            "end": end_dt,
            "duration_minutes": duration_minutes,
        }
        await handle_calendar_add(update, context, event_info)
        return

    mode = args[0].lower() if args else "today"
    mode = mode.strip()
    remaining_args = args[1:] if len(args) > 1 else []

    def fetch_events():
        try:
            title = "오늘 일정"
            if mode in {"today", "t", "오늘"}:
                events = calendar_service.get_today_events()
                title = "오늘 일정"
            elif mode in {"tomorrow", "tmr", "내일"}:
                events = calendar_service.get_tomorrow_events()
                title = "내일 일정"
            elif mode in {"week", "w", "주간"}:
                events = calendar_service.get_week_events()
                title = "이번 주 일정"
            elif mode in {"upcoming", "next", "예정"}:
                minutes = 60
                if remaining_args:
                    try:
                        minutes = max(10, min(int(remaining_args[0]), 1440))
                    except ValueError:
                        minutes = 60
                events = calendar_service.get_upcoming_events(minutes_ahead=minutes)
                title = f"향후 {minutes}분 이내 일정"
            elif mode in {"search", "find"} and remaining_args:
                query = " ".join(remaining_args)
                events = calendar_service.search_events(query)
                title = f"검색 결과: {query}"
            else:
                query = " ".join(args)
                if query:
                    events = calendar_service.search_events(query)
                    title = f"검색 결과: {query}"
                else:
                    events = calendar_service.get_today_events()
                    title = "오늘 일정"

            formatted = calendar_service.format_event_list(events, title)
            return True, simplify_markdown(formatted)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Calendar fetch failed: %s", exc)
            return False, f"Google Calendar에서 일정을 가져오는 중 오류가 발생했습니다: {exc}"

    success, result = await asyncio.to_thread(fetch_events)

    if not success:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ {result}")
        return

    chunks = split_into_chunks(result, limit=3500)
    for chunk in chunks:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


async def handle_calendar_add(update: Update, context: ContextTypes.DEFAULT_TYPE, event_info: Dict[str, Any]):
    """Create a new calendar event."""
    chat_id = update.effective_chat.id
    summary = event_info["summary"]
    start_dt = event_info["start"]
    end_dt = event_info["end"]

    await context.bot.send_message(
        chat_id=chat_id,
        text=(f"📅 '{summary}' 일정을 {start_dt.strftime('%Y-%m-%d %H:%M')}에 등록합니다...")
    )

    def create_event():
        try:
            return True, calendar_service.create_event(
                summary=summary,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Calendar create failed: %s", exc)
            return False, str(exc)

    success, result = await asyncio.to_thread(create_event)

    if not success:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ 일정을 생성하는 중 오류가 발생했습니다: {result}\n"
                 "캘린더 공유 및 서비스 계정 권한을 다시 확인해주세요.",
        )
        return

    created_event = result
    start_str = start_dt.strftime("%Y-%m-%d %H:%M")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M")
    link = created_event.get("htmlLink")

    lines = [
        "✅ 일정이 등록되었습니다!",
        f"- 제목: {summary}",
        f"- 시작: {start_str}",
        f"- 종료: {end_str}",
    ]
    if link:
        lines.append(f"- 링크: {link}")

    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines))
    return


async def handle_drive_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /drive command - show Drive usage guide."""
    help_text = (
        "📁 **Google Drive 사용 가이드**\n\n"
        "**명령어**\n"
        "- `/drive` - 이 도움말 보기\n"
        "- `/drivelist` - 기본 폴더 파일 목록 보기\n"
        "- `/driveget <file_id>` - 특정 파일 다운로드\n"
        "- `/drivesync` - 새로 업로드된 파일 확인\n\n"
        "**팁**\n"
        "- 폴더 ID를 알고 있다면 `/drivelist <folder_id>` 로 하위 폴더도 확인할 수 있어요.\n"
        "- 새 파일이 올라왔는지 빠르게 확인하려면 `/drivesync` 를 사용해주세요."
    )

    await update.message.reply_text(help_text)


async def handle_drive_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    args_override: Optional[List[str]] = None,
):
    """Handle /drivelist command - list Google Drive files."""
    args = args_override if args_override is not None else (getattr(context, "args", []) or [])
    folder_id = args[0] if args else None

    progress = await update.message.reply_text("📁 드라이브 파일 목록을 불러오는 중입니다...")

    try:
        files = await asyncio.to_thread(get_folder_files, folder_id)
        message = await asyncio.to_thread(format_file_list, files)
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text=message,
            parse_mode="Markdown",
        )
    except Exception as exc:  # pragma: no cover - 방어적 처리
        logger.error("Drive list error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text="❌ 드라이브 목록을 불러오지 못했습니다.",
        )


async def handle_drive_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /drivesync command - check for new Drive files."""
    progress = await update.message.reply_text("🔍 드라이브 새 파일을 확인하는 중입니다...")

    try:
        new_files = await asyncio.to_thread(check_new_files)

        if not new_files:
            text = "📭 새로 업로드된 파일이 없습니다."
        else:
            lines = [f"🆕 새 파일 {len(new_files)}개 발견!"]
            for index, file in enumerate(new_files, 1):
                name = file.get("name", "이름 없음")
                file_id = file.get("id", "-")
                mime_type = file.get("mimeType", "-")
                lines.append(f"{index}. {name} ({mime_type})\n   ID: `{file_id}`")
            text = "\n".join(lines)

        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text=text,
            parse_mode="Markdown",
        )
    except Exception as exc:  # pragma: no cover - 방어적 처리
        logger.error("Drive sync error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=progress.chat_id,
            message_id=progress.message_id,
            text="❌ 드라이브 새 파일을 확인하는 중 오류가 발생했습니다.",
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("handle_document entered")
    """Handle document uploads"""
    doc = update.message.document
    if not doc:
        return

    chat_id = str(update.effective_chat.id)
    filename = doc.file_name or "document"
    file_size = doc.file_size or 0

    logger.info(f"Document upload: {filename} ({file_size} bytes)")
    logger.info(f"Document MIME type: {getattr(doc, 'mime_type', 'N/A')}")

    # Check if it's an audio file - send to audio bot
    if is_audio_file(filename):
        logger.info(f"Detected audio file: {filename}, sending to audio bot")
        return await handle_document_as_audio(update, context, doc)

    if not is_document_file(filename) and not is_text_file(filename):
        await update.message.reply_text(
            f"⚠️ WARN: {filename}\n지원 형식: PDF, DOCX, TXT, CSV, 오디오 파일"
        )
        return

    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        await update.message.reply_text(
            f"⚠️ WARN: 파일이 너무 큽니다 (최대 50MB)\n현재 크기: {file_size / (1024*1024):.1f}MB"
        )
        return

    await update.message.reply_text(
        f"📄 문서를 받았습니다!\n파일: {filename}\n크기: {file_size / 1024:.1f}KB"
    )

    task_id = str(uuid4())
    active_tasks.setdefault(chat_id, {})[task_id] = {
        "type": "document",
        "status": "processing",
        "file_name": filename,
        "file_id": doc.file_id,
        "mime_type": getattr(doc, "mime_type", None),
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(doc.file_id)
        import tempfile
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"doc_{chat_id}_{filename}")
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded document to {file_path}")
    except Exception as exc:
        logger.error(f"Error downloading file: {exc}")
        await update.message.reply_text("❌ ERROR: 파일 다운로드 실패.")
        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "document",
        {
            "task_id": task_id,
            "chat_id": chat_id,
            "file_data": {
                "file_path": file_path,
                "file_name": filename,
                "file_size": file_size,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent document task to document bot for chat {chat_id}")

    estimated_time = estimate_processing_time("document", {"file_name": filename, "file_size": file_size})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), task_id, "document", estimated_time, cancel_event)
    )

    async def process_document_result():
        try:
            result_payload = await wait_for_result(task_id, timeout=1800)
        finally:
            cancel_event.set()
            await progress_task

        if result_payload:
            await _process_result_payload(context.bot, result_payload)
        else:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text="⏱️ 처리 시간이 초과되었습니다. 다시 시도해주세요.",
            )

        if file_path:
            try:
                os.remove(file_path)
            except Exception:
                pass

        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)

    asyncio.create_task(process_document_result())
    return


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle standalone audio files (non-voice) uploaded by users."""
    audio = update.message.audio
    if not audio:
        return

    logger.info("handle_audio entered")
    logger.info(
        "Audio upload: %s (%s bytes)",
        getattr(audio, "file_name", None) or audio.file_id,
        getattr(audio, "file_size", 0),
    )

    await handle_document_as_audio(update, context, audio)


async def handle_document_as_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, doc):
    logger.info("handle_document_as_audio entered")
    """Handle audio files uploaded as documents"""
    chat_id = str(update.effective_chat.id)
    filename = doc.file_name or "audio"
    file_size = doc.file_size or 0

    logger.info(f"Audio document upload: {filename} ({file_size} bytes)")

    await update.message.reply_text(
        f"🎤 오디오 파일을 받았습니다!\n파일: {filename}\n크기: {file_size / 1024:.1f}KB"
    )

    task_id = str(uuid4())
    active_tasks.setdefault(chat_id, {})[task_id] = {
        "type": "audio",
        "status": "processing",
        "file_name": filename,
        "file_id": doc.file_id,
        "mime_type": getattr(doc, "mime_type", "audio/mpeg"),
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(doc.file_id)
        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"audio_doc_{chat_id}_{int(time.time())}_{filename}")
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded audio document to: {file_path}")

    except Exception as exc:
        logger.error(f"Error downloading audio document: {exc}")
        await update.message.reply_text("❌ ERROR: 오디오 파일 다운로드 실패.")
        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "audio",
        {
            "task_id": task_id,
            "chat_id": chat_id,
            "voice_data": {
                "file_path": file_path,
                "duration": 0,  # Duration unknown for uploaded files
                "mime_type": getattr(doc, "mime_type", "audio/mpeg"),
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent audio document task to audio bot for chat {chat_id}")

    # Use default estimation for unknown duration
    estimated_time = estimate_processing_time("audio", {"duration": 60})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), task_id, "audio", estimated_time, cancel_event)
    )

    async def process_audio_result():
        try:
            result_payload = await wait_for_result(task_id, timeout=1800)
        finally:
            cancel_event.set()
            await progress_task

        if result_payload:
            await _process_result_payload(context.bot, result_payload)
        else:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text="⏰ 오디오 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요.",
            )
            try:
                os.remove(file_path)
            except Exception:
                pass

        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)

    asyncio.create_task(process_audio_result())
    return


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    logger.info(">>> handle_voice CALLED! <<<")
    logger.info(f"update.message type: {type(update.message)}")
    logger.info(f"update.message content: {update.message}")
    logger.info(f"update.message.voice: {update.message.voice}")
    logger.info(f"update.message.audio: {getattr(update.message, 'audio', 'N/A')}")
    logger.info(f"update.message.document: {getattr(update.message, 'document', 'N/A')}")

    voice = update.message.voice
    logger.info(f"voice object: {voice}")

    if not voice:
        logger.warning("❌ No voice object in message")
        return

    chat_id = str(update.effective_chat.id)
    logger.info(f"chat_id: {chat_id}")

    duration = voice.duration or 0
    logger.info(f"Duration: {duration}s")
    logger.info(f"MIME type: {voice.mime_type}")
    logger.info(f"File ID: {voice.file_id}")

    if not voice.mime_type or not voice.mime_type.startswith('audio/'):
        logger.warning(f"❌ Voice message has unsupported MIME type: {voice.mime_type}. Returning early.")
        await update.message.reply_text("⚠️ WARN: 음성 파일 형식이 올바르지 않습니다.")
        return

    logger.info("✅ Voice validation passed, sending response...")
    await update.message.reply_text(
        f"🎤 음성을 받았습니다!\n길이: {duration}초"
    )
    logger.info("✅ Response sent successfully!")

    task_id = str(uuid4())
    active_tasks.setdefault(chat_id, {})[task_id] = {
        "type": "audio",
        "status": "processing",
        "duration": duration,
        "file_id": voice.file_id,
        "mime_type": voice.mime_type,
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(voice.file_id)

        ext_map = {
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
        }
        file_ext = ext_map.get(voice.mime_type, '.ogg')

        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"voice_{chat_id}_{int(time.time())}{file_ext}")
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded voice to: {file_path}")
        active_tasks[chat_id][task_id]["file_name"] = os.path.basename(file_path)

    except Exception as exc:
        logger.error(f"Error downloading voice: {exc}")
        await update.message.reply_text("❌ ERROR: 음성 다운로드 실패.")
        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "audio",
        {
            "task_id": task_id,
            "chat_id": chat_id,
            "voice_data": {
                "file_path": file_path,
                "duration": duration,
                "mime_type": voice.mime_type,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent voice task to audio bot for chat {chat_id}")

    estimated_time = estimate_processing_time("audio", {"duration": duration})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), task_id, "audio", estimated_time, cancel_event)
    )

    async def process_audio_result():
        try:
            result_payload = await wait_for_result(task_id, timeout=1800)
        finally:
            cancel_event.set()
            await progress_task

        if result_payload:
            await _process_result_payload(context.bot, result_payload)
        else:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text="⏰ 음성 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요.",
            )
            try:
                os.remove(file_path)
            except Exception:
                pass

        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)

    asyncio.create_task(process_audio_result())
    return
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads"""
    photo = update.message.photo[-1]
    if not photo:
        return

    chat_id = str(update.effective_chat.id)
    file_id = photo.file_id

    logger.info(f"Photo upload: {file_id}")

    await update.message.reply_text("🖼️ 이미지를 받았습니다!")

    task_id = str(uuid4())
    active_tasks.setdefault(chat_id, {})[task_id] = {
        "type": "image",
        "status": "processing",
        "file_id": file_id,
        "mime_type": "image/jpeg",
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(file_id)
        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        file_name = f"image_{chat_id}_{int(time.time())}.jpg"
        file_path = os.path.join(temp_dir, file_name)
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded image to: {file_path}")
        active_tasks[chat_id][task_id]["file_name"] = file_name
    except Exception as exc:
        logger.error(f"Error downloading image: {exc}")
        await update.message.reply_text("❌ ERROR: 이미지 다운로드 실패.")
        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "image",
        {
            "task_id": task_id,
            "chat_id": chat_id,
            "image_data": {
                "file_path": file_path,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent image task to image bot for chat {chat_id}")

    estimated_time = estimate_processing_time("image", {})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), task_id, "image", estimated_time, cancel_event)
    )

    async def process_image_result():
        try:
            result_payload = await wait_for_result(task_id, timeout=1800)
        finally:
            cancel_event.set()
            await progress_task

        if result_payload:
            await _process_result_payload(context.bot, result_payload)
        else:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text="⏰ 이미지 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요.",
            )
            if file_path:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

        chat_tasks = active_tasks.get(chat_id, {})
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)

    asyncio.create_task(process_image_result())
    return
async def _process_result_payload(bot: Bot, payload: Dict[str, Any]):
    """Process a single result payload coming from Redis."""
    chat_id = str(payload.get("chat_id") or "")
    result = payload.get("result", {})
    bot_name = payload.get("bot_name", "unknown")
    task_id = payload.get("task_id")

    if not chat_id:
        logger.warning("Result payload missing chat_id: %s", payload)
        return

    if not task_id:
        logger.warning("Result payload missing task_id: %s", payload)
        task_id = next(iter(active_tasks.get(chat_id, {})), None)

    chat_tasks = active_tasks.get(chat_id, {})

    if not task_id or task_id not in chat_tasks:
        logger.warning("Received result for inactive chat %s", chat_id)
        return

    task_info = chat_tasks.get(task_id, {})

    try:
        if bot_name == "document_bot":
            await send_document_result(bot, chat_id, task_id, result, task_info)
        elif bot_name == "audio_bot":
            await send_audio_result(bot, chat_id, task_id, result, task_info)
        elif bot_name == "image_bot":
            await send_image_result(bot, chat_id, task_id, result, task_info)
        else:
            logger.warning("Unknown bot_name in result payload: %s", bot_name)
            await bot.send_message(
                chat_id=int(chat_id),
                text="처리 결과를 받았지만 어떤 전문봇에서 왔는지 확인할 수 없어요."
            )
    finally:
        chat_tasks.pop(task_id, None)
        if not chat_tasks:
            active_tasks.pop(chat_id, None)
        logger.info("Completed task %s for chat %s", task_id, chat_id)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses for automation preferences."""
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    chat_id = str(query.message.chat.id if query.message else query.from_user.id)

    try:
        await query.answer()
    except Exception as exc:
        logger.warning("Failed to answer callback query: %s", exc)

    if data.startswith("follow|"):
        parts = data.split("|")
        if len(parts) != 4:
            return
        _, task_id, mode, action = parts

        record = followup_tasks.get(task_id)
        if not record or record.get("chat_id") != chat_id:
            await query.edit_message_text("⚠️ 처리할 결과를 찾지 못했어요. 다시 시도해주세요.")
            return

        task_type = record.get("task_type", "document")

        if mode == "once":
            if action != "none":
                await execute_followup_action(action, context.bot, chat_id, record)
            else:
                try:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text="추가 작업 없이 마무리했어요.",
                    )
                except Exception as exc:
                    logger.error("Failed to send no-action confirmation: %s", exc)
            followup_tasks.pop(task_id, None)
            await query.edit_message_text("✅ 선택한 작업을 완료했습니다.")
            return

        if mode == "auto":
            prefs = set_default_action_for_type(chat_id, task_type, action)
            prefs = preference_store.set_preferences(chat_id, {"mode": "auto", "default_actions": prefs["default_actions"]})
            action_label = format_action_label(action)
            await query.edit_message_text(
                f"🔁 앞으로 \"{action_label}\" 작업을 자동으로 실행할게요.",
            )
            if action != "none":
                await execute_followup_action(action, context.bot, chat_id, record)
            followup_tasks.pop(task_id, None)
            prefs = preference_store.get_preferences(chat_id)
            await apply_preferences_to_pending_tasks(context.bot, chat_id, task_type, prefs)
            return

        if mode == "skip":
            prefs = set_default_action_for_type(chat_id, task_type, "none")
            preference_store.set_preferences(chat_id, {"mode": "skip", "default_actions": prefs["default_actions"]})
            followup_tasks.pop(task_id, None)
            await query.edit_message_text("앞으로 결과만 전달하고 후속 작업은 건너뛰겠습니다.")
            prefs = preference_store.get_preferences(chat_id)
            await apply_preferences_to_pending_tasks(context.bot, chat_id, None, prefs)
            return

    elif data.startswith("pref_mode|"):
        _, mode = data.split("|", 1)
        if mode == "auto":
            prefs = preference_store.set_preferences(chat_id, {"mode": "auto"})
        elif mode == "skip":
            prefs = preference_store.set_preferences(chat_id, {"mode": "skip"})
        else:
            prefs = preference_store.set_preferences(chat_id, {"mode": "ask"})

        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )
        await apply_preferences_to_pending_tasks(context.bot, chat_id, None, prefs)

    elif data.startswith("pref_action|"):
        _, task_type, action = data.split("|", 2)
        if action == "none":
            prefs = set_default_action_for_type(chat_id, task_type, "none")
            prefs = preference_store.set_preferences(chat_id, {"mode": "ask", "default_actions": prefs["default_actions"]})
        else:
            prefs = set_default_action_for_type(chat_id, task_type, action)
            prefs = preference_store.set_preferences(chat_id, {"mode": "auto", "default_actions": prefs["default_actions"]})
        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )
        await apply_preferences_to_pending_tasks(context.bot, chat_id, task_type, prefs)

    elif data.startswith("pref_open|"):
        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )

    elif data.startswith("pref_pipeline|"):
        _, pipeline = data.split("|", 1)
        preset = PIPELINE_PRESETS.get(pipeline)
        if not preset:
            await query.edit_message_text("⚠️ 해당 파이프라인을 찾지 못했습니다.")
            return

        previous = preference_store.get_preferences(chat_id)
        preference_history.setdefault(chat_id, []).append(previous)
        preference_history[chat_id] = preference_history[chat_id][-PREFERENCE_HISTORY_LIMIT:]

        defaults = build_default_actions_summary(previous)
        defaults.update(preset)
        preference_store.set_preferences(chat_id, {
            "default_actions": defaults,
            "mode": "auto",
        })

        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            f"✅ {PIPELINE_PRESET_LABELS.get(pipeline, pipeline)} 적용 완료!",
        )
        await query.message.reply_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )
        await apply_preferences_to_pending_tasks(context.bot, chat_id, None, prefs)

    elif data.startswith("pref_undo|"):
        history = preference_history.get(chat_id, [])
        if not history:
            await query.edit_message_text("되돌릴 설정이 없습니다.")
            return

        previous = history.pop()
        preference_store.set_preferences(chat_id, previous)
        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text("↩️ 설정을 이전 상태로 되돌렸어요.")
        await query.message.reply_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )

    elif data.startswith("pref_integration|"):
        _, integration, action = data.split("|", 2)
        prefs = preference_store.get_preferences(chat_id)
        integrations = prefs.get("integrations", {}).copy()
        if action == "toggle":
            current = integrations.get(integration, True)
            integrations[integration] = not current
        else:
            integrations[integration] = action == "on"

        preference_history.setdefault(chat_id, []).append(prefs)
        preference_history[chat_id] = preference_history[chat_id][-PREFERENCE_HISTORY_LIMIT:]

        preference_store.set_preferences(chat_id, {"integrations": integrations})
        updated = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(updated),
            reply_markup=build_settings_keyboard(updated),
        )


async def poll_result_messages(context: CallbackContext) -> None:
    """Periodically consume result messages from Redis and dispatch to users."""
    if not pending_results:
        return

    if not messenger.pubsub:
        return

    try:
        message = await asyncio.to_thread(
            messenger.pubsub.get_message,
            ignore_subscribe_messages=True,
            timeout=2.0,
        )

        while message:
            if message.get("type") == "message":
                data = message.get("data")
                try:
                    payload = json.loads(data) if isinstance(data, str) else data
                except json.JSONDecodeError as exc:
                    logger.error("Invalid JSON in result payload: %s", exc)
                    payload = None

                if isinstance(payload, dict):
                    task_id = payload.get("task_id")
                    if task_id and task_id in pending_results:
                        pending_results[task_id]["result"] = payload
                        pending_results[task_id]["event"].set()
                    else:
                        await _process_result_payload(context.bot, payload)
                else:
                    logger.warning("Unexpected payload type from Redis: %r", payload)

            message = await asyncio.to_thread(
                messenger.pubsub.get_message,
                ignore_subscribe_messages=True,
                timeout=2.0,
            )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Result listener error: %s", exc)


async def wait_for_result(task_id: str, timeout: int = 1800) -> Optional[Dict[str, Any]]:
    """Wait for a result payload from specialized bots."""
    event = asyncio.Event()
    pending_results[task_id] = {"event": event, "result": None}

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return pending_results.get(task_id, {}).get("result")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for result for task %s", task_id)
        return None
    finally:
        pending_results.pop(task_id, None)


async def send_document_result(bot: Bot, chat_id: str, task_id: str, result: Dict, task_info: Dict[str, Any]):
    """Send document analysis result and trigger follow-up flow."""
    if result.get("error"):
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"❌ 문서 분석 중 오류가 발생했습니다: {result['error']}",
            )
        except Exception as exc:
            logger.error("Error sending document failure: %s", exc)
        followup_tasks.pop(task_id, None)
        return

    summary = result.get("summary", "N/A")
    extracted = result.get("text", "N/A")
    file_name = result.get("file_name", "문서")

    summary_clean = simplify_markdown(summary)
    excerpt_clean = simplify_markdown(extracted)

    if len(summary_clean) > 1500:
        summary_clean = summary_clean[:1500] + "\n\n...[요약 일부 생략]"
    if len(excerpt_clean) > 1500:
        excerpt_clean = excerpt_clean[:1500] + "\n\n...[원문 발췌 일부 생략]"

    message = (
        f"📄 문서 분석 완료!\n"
        f"파일명: {file_name}\n\n"
        f"[요약]\n{summary_clean or '(요약이 비어 있습니다)'}\n\n"
        f"[원문 발췌]\n{excerpt_clean or '(본문이 비어 있습니다)'}"
    )

    try:
        await bot.send_message(chat_id=int(chat_id), text=message)
    except Exception as exc:
        logger.error("Error sending document result: %s", exc)

    meta = {
        "file_id": task_info.get("file_id"),
        "file_name": task_info.get("file_name"),
        "mime_type": task_info.get("mime_type"),
    }
    register_followup_task(task_id, chat_id, "document", result, meta)
    prefs = preference_store.get_preferences(chat_id)
    await apply_preferences_to_task(bot, chat_id, task_id, "document", prefs)


async def send_audio_result(bot: Bot, chat_id: str, task_id: str, result: Dict, task_info: Dict[str, Any]):
    """Send audio transcription result to user"""
    if result.get("error"):
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"❌ 오디오 처리 중 오류가 발생했습니다: {result['error']}",
            )
        except Exception as exc:
            logger.error("Error sending audio failure: %s", exc)
        followup_tasks.pop(task_id, None)
        return

    transcription = simplify_markdown(result.get("transcription", ""))
    summary = simplify_markdown(result.get("summary", ""))

    if len(transcription) > 1500:
        transcription = transcription[:1500] + "\n\n...[전사 일부 생략]"
    if len(summary) > 1500:
        summary = summary[:1500] + "\n\n...[요약 일부 생략]"

    message = (
        "🎤 오디오 분석 완료!\n"
        f"길이: {result.get('duration', 0)}초\n\n"
        f"[전사]\n{transcription or '(전사 없음)'}\n\n"
        f"[요약]\n{summary or '(요약 없음)'}"
    )

    try:
        await bot.send_message(chat_id=int(chat_id), text=message)
    except Exception as e:
        logger.error(f"Error sending audio result: {e}")

    meta = {
        "file_id": task_info.get("file_id"),
        "file_name": task_info.get("file_name"),
        "mime_type": task_info.get("mime_type"),
    }
    register_followup_task(task_id, chat_id, "audio", result, meta)
    prefs = preference_store.get_preferences(chat_id)
    await apply_preferences_to_task(bot, chat_id, task_id, "audio", prefs)


async def send_image_result(bot: Bot, chat_id: str, task_id: str, result: Dict, task_info: Dict[str, Any]):
    """Send image analysis result to user"""
    if result.get("error"):
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"❌ 이미지 분석 중 오류가 발생했습니다: {result['error']}",
            )
        except Exception as exc:
            logger.error("Error sending image failure: %s", exc)
        followup_tasks.pop(task_id, None)
        return

    description = simplify_markdown(result.get("description", ""))
    analysis = simplify_markdown(result.get("analysis", ""))

    # Completely removed length limits
    message = (
        "🖼️ 이미지 분석 완료!\n\n"
        f"[설명]\n{description or '(설명 없음)'}\n\n"
        f"[분석]\n{analysis or '(분석 없음)'}"
    )

    try:
        await bot.send_message(chat_id=int(chat_id), text=message)
    except Exception as e:
        logger.error(f"Error sending image result: {e}")

    # Skip follow-up tasks (disable Drive save prompts)
    # If you want to re-enable, comment out the lines below
    # or set mode to 'ask' in /settings
    logger.info(f"Image result sent, skipping follow-up tasks for task_id {task_id}")
    # register_followup_task(task_id, chat_id, "image", result, meta)
    # prefs = preference_store.get_preferences(chat_id)
    # await apply_preferences_to_task(bot, chat_id, task_id, "image", prefs)


def main():
    """Main function"""
    print("=== Main Bot (Task Distributor) ===")

    if not MAIN_BOT_TOKEN:
        print("[ERROR] ERROR: MAIN_BOT_TOKEN is missing")
        print("Please set MAIN_BOT_TOKEN in .env file")
        return

    # Create application
    application = Application.builder().token(MAIN_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_help))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("bots", handle_bots))
    application.add_handler(CommandHandler("gmail", handle_gmail))
    application.add_handler(CommandHandler("calendar", handle_calendar))
    application.add_handler(CommandHandler("settings", handle_settings))
    application.add_handler(CommandHandler("remind", handle_reminder_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Start bot
    print("[OK] Bot is running...")
    print("Press Ctrl+C to stop")

    if REDIS_ENABLED and messenger.pubsub:
        messenger.pubsub.subscribe("main_bot_results")
        if application.job_queue:
            application.job_queue.run_repeating(
                poll_result_messages,
                interval=1.0,
                name="result_listener",
            )
            logger.info("Result listener scheduled via job queue")
        else:
            logger.warning(
                "JobQueue not available; falling back to manual Redis polling loop."
            )

            async def _post_init(app: Application) -> None:
                if manual_result_listener_task.get("task") is None:
                    manual_result_listener_task["task"] = app.create_task(manual_result_listener(app.bot))

            async def _post_shutdown(app: Application) -> None:
                task = manual_result_listener_task.get("task")
                if task:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                    manual_result_listener_task["task"] = None

            application.post_init = _post_init
            application.post_shutdown = _post_shutdown
    else:
        logger.info("Redis disabled or unavailable; skipping result listener")

    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\nBYE Shutting down...")
    finally:
        task = manual_result_listener_task.get("task")
        if task:
            task.cancel()
            manual_result_listener_task["task"] = None
        messenger.close()


if __name__ == "__main__":
    import asyncio
    main()
