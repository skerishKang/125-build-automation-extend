"""/calendar 명령 및 달력 관련 자연어 처리 핸들러."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from backend.services import calendar_service  # type: ignore

from ..utils.text_utils import simplify_markdown, split_into_chunks
from ..utils.datetime_utils import parse_relative_date_time


async def handle_calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    args_override: Optional[List[str]] = None,
) -> None:
    """/calendar 명령 처리."""

    chat_id = update.effective_chat.id
    args = args_override if args_override is not None else (getattr(context, "args", []) or [])

    if args and args[0].lower() == "add":
        await _handle_calendar_add(update, context, args[1:])
        return

    mode = args[0].lower() if args else "today"
    mode = mode.strip()
    remaining_args = args[1:] if len(args) > 1 else []

    def fetch_events() -> Dict[str, str]:
        try:
            title = "오늘 일정"
            if mode in {"today", "t", "오늘"}:
                events = calendar_service.get_today_events()
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
            formatted = calendar_service.format_event_list(events, title)
            return {"success": True, "message": simplify_markdown(formatted)}
        except Exception as exc:  # pragma: no cover
            return {
                "success": False,
                "message": f"Google Calendar에서 일정을 가져오는 중 오류가 발생했습니다: {exc}",
            }

    result = await asyncio.to_thread(fetch_events)

    if not result.get("success", False):
        await context.bot.send_message(chat_id=chat_id, text=f"❌ {result['message']}")
        return

    chunks = split_into_chunks(result["message"], limit=3500)
    for chunk in chunks:
        await context.bot.send_message(chat_id=chat_id, text=chunk)


async def handle_calendar_add(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    event_info: Optional[Dict[str, any]] = None,
) -> None:
    """/calendar add 서브 명령 처리."""

    chat_id = update.effective_chat.id

    if not event_info:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ 올바른 형식이 아닙니다. 예: `/calendar add 회의 | 2025-11-07 | 15:00 | 90`",
        )
        return

    result = calendar_service.create_event(event_info)
    if result.get("success"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ 일정을 추가했습니다!\n"
                f"제목: {event_info['summary']}\n"
                f"시작: {event_info['start']}\n"
                f"종료: {event_info['end']}"
            ),
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ 일정을 추가하는 중 문제가 발생했습니다. 다시 시도해주세요.",
        )


async def handle_calendar_natural_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    """자연어로 전달된 일정 추가 요청 처리."""

    parsed = parse_relative_date_time(text)
    if not parsed:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ 일정을 이해하지 못했습니다. 날짜와 시간을 다시 확인해주세요.",
        )
        return

    summary = text.split(" ")[0] if text else "일정"
    event_info = {
        "summary": summary,
        "start": parsed["start"],
        "end": parsed["end"],
        "duration_minutes": parsed["duration_minutes"],
    }
    await handle_calendar_add(update, context, event_info)
