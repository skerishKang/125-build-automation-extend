"""Calendar command handlers for the unified Telegram bot runtime."""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from telegram import Update
    from telegram.ext import ContextTypes


def _ensure_backend_path() -> None:
    backend_path = os.path.join(os.path.dirname(__file__), "..")
    backend_path = os.path.abspath(backend_path)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


async def handle_cal_on(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_on command - start Calendar monitoring."""
    reply_text = runtime.reply_text
    logger = runtime.logger
    state = runtime.calendar_monitoring_state

    if state["enabled"]:
        await reply_text(
            update,
            "🟡 **Calendar 감시가 이미 실행 중이에요!**\n"
            f"- 현재까지 {state['total_alerts']}개 알림 보냄\n"
            "- `/cal_status`로 상세 상태 확인",
        )
        return

    test_msg = await reply_text(update, "🗓️ Calendar 연결 테스트 중...")

    try:
        _ensure_backend_path()
        from backend.services.calendar import get_calendar_service  # noqa: WPS433

        calendar_service = get_calendar_service()
        calendar_service.get_today_events()

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text="✅ Calendar 연결 성공! 감시를 시작합니다...",
        )

        state["enabled"] = True
        state["total_alerts"] = 0
        state["start_time"] = datetime.now().isoformat()
        state["alerted_events"] = set()
        start_calendar_monitoring(runtime)

        await asyncio.sleep(1)

        final_msg = """
🟢 **Calendar 실시간 감시 시작!**

📋 **감시 설정**:
- 확인 주기: 5분마다
- 대상: 다가오는 일정 (30분 전 알림)
- AI 분석: Gemini 2.5 Flash
- 즉시 텔레그램 알림

💡 **명령어**:
- `/cal_off` - 감시 중지
- `/cal_status` - 상태 확인
- `/cal_today` - 오늘 일정
- `/cal_tomorrow` - 내일 일정
- `/cal_week` - 이번 주 일정
- `/cal_search <키워드>` - 일정 검색
        """.strip()

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text=final_msg,
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calendar start error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text=f"❌ Calendar 연결 실패: {str(exc)[:100]}",
        )


async def handle_cal_off(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_off command - stop Calendar monitoring."""
    reply_text = runtime.reply_text
    state = runtime.calendar_monitoring_state

    if not state["enabled"]:
        await reply_text(update, "🔴 Calendar 감시가 이미 중지되어 있어요!")
        return

    state["enabled"] = False
    total_alerts = state.get("total_alerts", 0)

    stop_message = f"""
📅 **Calendar 감시 중지됨**

📊 **이번 세션 통계**:
- 보낸 알림: {total_alerts}개
- 감시 시간: {state.get('start_time', '확인 불가')}부터

💡 **재시작하려면**:
- `/cal_on` - 감시 다시 시작
- `/cal_today` - 수동으로 오늘 일정 확인
    """.strip()

    await reply_text(update, stop_message)


async def handle_cal_status(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_status command - check Calendar monitoring status."""
    reply_text = runtime.reply_text
    logger = runtime.logger
    state = runtime.calendar_monitoring_state

    status_icon = "🟢" if state["enabled"] else "🔴"
    status_text = "실행 중" if state["enabled"] else "중지됨"

    last_check = state.get("last_check", "없음")
    total_alerts = state.get("total_alerts", 0)

    if state["enabled"]:
        try:
            _ensure_backend_path()
            from backend.services.calendar import get_calendar_service  # noqa: WPS433

            calendar_service = get_calendar_service()
            today_count = len(calendar_service.get_today_events())
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Calendar today count failed: %s", exc)
            today_count = "확인 불가"
    else:
        today_count = "감시 중지됨"

    status_message = f"""
📊 **Calendar 감시 상태**

{status_icon} **상태**: {status_text}
🕒 **마지막 확인**: {last_check}
📅 **보낸 알림**: {total_alerts}개
📋 **오늘 일정**: {today_count}개

⚙️ **설정**:
- 확인 주기: 5분마다
- 알림: 30분 전 일정
- AI 분석: Gemini 2.5 Flash

💡 **사용 가능한 명령어**:
- `/cal_on` - 감시 시작
- `/cal_off` - 감시 중지
- `/cal_today` - 오늘 일정
- `/cal_tomorrow` - 내일 일정
- `/cal_week` - 이번 주 일정
- `/cal_search <키워드>` - 일정 검색
    """.strip()

    await reply_text(update, status_message)


async def _send_calendar_list(
    runtime: Any,
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    fetcher_name: str,
    title: str,
    progress_message: str,
) -> None:
    reply_text = runtime.reply_text
    logger = runtime.logger

    ack_msg = await reply_text(update, progress_message)

    try:
        _ensure_backend_path()
        from backend.services.calendar import (  # noqa: WPS433
            get_calendar_service,
            format_event_list,
        )

        calendar_service = get_calendar_service()
        fetcher = getattr(calendar_service, fetcher_name)
        events = fetcher()

        result = format_event_list(events, title)

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=result,
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calendar %s error: %s", fetcher_name, exc)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=f"❌ 일정 조회 중 오류가 발생했어요: {str(exc)[:100]}",
        )


async def handle_cal_today(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_today command - show today's events."""
    await _send_calendar_list(
        runtime,
        update,
        context,
        fetcher_name="get_today_events",
        title="오늘의 일정",
        progress_message="🗓️ 오늘 일정 조회 중...",
    )


async def handle_cal_tomorrow(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_tomorrow command - show tomorrow's events."""
    await _send_calendar_list(
        runtime,
        update,
        context,
        fetcher_name="get_tomorrow_events",
        title="내일의 일정",
        progress_message="🗓️ 내일 일정 조회 중...",
    )


async def handle_cal_week(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_week command - show this week's events."""
    await _send_calendar_list(
        runtime,
        update,
        context,
        fetcher_name="get_week_events",
        title="이번 주 일정",
        progress_message="🗓️ 이번 주 일정 조회 중...",
    )


async def handle_cal_search(runtime: Any, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Handle /cal_search command - search for events."""
    reply_text = runtime.reply_text
    logger = runtime.logger

    args = context.args
    if not args:
        await reply_text(update, "사용법: `/cal_search <검색어>`\n\n예: `/cal_search 미팅`")
        return

    search_query = " ".join(args)
    ack_msg = await reply_text(update, f"🔍 '{search_query}' 일정 검색 중...")

    try:
        _ensure_backend_path()
        from backend.services.calendar import (  # noqa: WPS433
            get_calendar_service,
            format_event_list,
        )

        calendar_service = get_calendar_service()
        search_results = calendar_service.search_events(search_query, max_results=20)

        result = format_event_list(search_results, f"검색 결과: {search_query}")

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=result,
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calendar search error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=f"❌ 일정 검색 중 오류가 발생했어요: {str(exc)[:100]}",
        )


def start_calendar_monitoring(runtime: Any) -> None:
    """Start Calendar monitoring in a background thread."""
    logger = runtime.logger
    state = runtime.calendar_monitoring_state

    if state["thread"] and state["thread"].is_alive():
        return

    state["thread"] = threading.Thread(
        target=calendar_monitor_loop,
        args=(runtime,),
        daemon=True,
    )
    state["thread"].start()
    logger.info("🗓️ Calendar monitoring started")


def calendar_monitor_loop(runtime: Any) -> None:
    """Background Calendar monitoring loop executed in thread."""
    logger = runtime.logger
    state = runtime.calendar_monitoring_state

    try:
        _ensure_backend_path()
        from backend.services.calendar import (  # noqa: WPS433
            get_calendar_service,
            get_upcoming_events,
        )

        calendar_service = get_calendar_service()

        logger.info("🗓️ Calendar monitoring worker started")

        while state["enabled"]:
            try:
                logger.info("🗓️ Checking for upcoming events...")

                upcoming_events = get_upcoming_events(minutes_ahead=30)
                new_alerts = []

                for event in upcoming_events:
                    event_id = event.get("id", "")

                    if event_id and event_id not in state["alerted_events"]:
                        new_alerts.append(event)
                        state["alerted_events"].add(event_id)

                if new_alerts:
                    logger.info("🗓️ Found %s upcoming events", len(new_alerts))
                    state["total_alerts"] += len(new_alerts)

                    for event_data in new_alerts:
                        asyncio.run_coroutine_threadsafe(
                            process_and_send_calendar_alert(runtime, event_data),
                            asyncio.get_event_loop(),
                        )

                state["last_check"] = datetime.now().strftime("%H:%M:%S")

                for _ in range(300):
                    if not state["enabled"]:
                        break
                    time.sleep(1)

            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Calendar monitoring error: %s", exc)
                time.sleep(60)

        logger.info("🗓️ Calendar monitoring worker stopped")

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calendar monitoring loop error: %s", exc)


async def monitor_calendar_events(runtime: Any) -> None:
    """Compat wrapper that awaits the monitoring loop within async context."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, calendar_monitor_loop, runtime)


async def process_and_send_calendar_alert(runtime: Any, event_data) -> None:
    """Process Calendar event and send alert to Telegram."""
    logger = runtime.logger
    app_instance = runtime._app_instance

    try:
        start = event_data.get("start", {})
        end = event_data.get("end", {})

        if "dateTime" in start:
            start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
            time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
        else:
            time_str = "종일"

        title = event_data.get("summary", "제목 없음")
        location = event_data.get("location", "")
        description = event_data.get("description", "")

        alert_message = f"""
🔔 **30분 후 일정 알림**

📅 **일정**: {title}
⏰ **시간**: {time_str}
        """.strip()

        if location:
            alert_message += f"\n📍 **장소**: {location}"

        if description:
            desc_preview = description[:100]
            if len(description) > 100:
                desc_preview += "..."
            alert_message += f"\n📝 **설명**: {desc_preview}"

        alert_message += "\n\n⏰ 준비하세요!"

        if app_instance and app_instance.chat_ids:
            for chat_id in app_instance.chat_ids:
                try:
                    await app_instance.bot.send_message(chat_id=chat_id, text=alert_message)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to send calendar alert to %s: %s", chat_id, exc)

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Calendar alert processing error: %s", exc)
