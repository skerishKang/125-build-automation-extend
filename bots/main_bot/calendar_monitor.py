"""
Google Calendar에서 다가오는 일정을 모니터링하여 텔레그램으로 알림을 보내는 스크립트.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

from telegram import Bot

from backend.services.calendar_service import (
    get_upcoming_events,
    format_event_datetime,
)
from backend.services import slack

logger = logging.getLogger("calendar_monitor")
logging.basicConfig(level=logging.INFO)

TELEGRAM_CHAT_ID = os.getenv("CALENDAR_ALERT_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
POLL_INTERVAL = int(os.getenv("CALENDAR_MONITOR_INTERVAL", "300"))  # 기본 5분
CALENDAR_ALERT_MINUTES = int(os.getenv("CALENDAR_ALERT_MINUTES", "30"))


def _validate_settings() -> Optional[str]:
    if not TELEGRAM_CHAT_ID:
        return "CALENDAR_ALERT_CHAT_ID 환경 변수가 필요합니다."
    if not TELEGRAM_BOT_TOKEN:
        return "MAIN_BOT_TOKEN 환경 변수가 필요합니다."
    return None


class CalendarAlertCache:
    """이미 알림을 전송한 이벤트를 추적하기 위한 캐시."""

    def __init__(self):
        self.sent_event_ids: set[str] = set()

    def filter_new_events(self, events: List[dict]) -> List[dict]:
        new_events = []
        for event in events:
            event_id = event.get("id")
            if event_id and event_id not in self.sent_event_ids:
                self.sent_event_ids.add(event_id)
                new_events.append(event)
        return new_events


def format_event_message(event: dict) -> str:
    summary = event.get("summary", "제목 없음")
    location = event.get("location", "")
    description = event.get("description", "")
    start = event.get("start", {})
    end = event.get("end", {})

    time_str = format_event_datetime(start, end)

    lines = [
        "🔔 곧 시작할 일정이 있어요!",
        f"• 제목: {summary}",
        f"• 시간: {time_str}",
    ]

    if location:
        lines.append(f"• 장소: {location}")

    if description:
        desc_preview = description.strip()
        if len(desc_preview) > 150:
            desc_preview = desc_preview[:150] + "..."
        lines.append(f"• 메모: {desc_preview}")

    html_link = event.get("htmlLink")
    if html_link:
        lines.append(f"• 보기: {html_link}")

    lines.append("\n⏰ 준비해주세요!")
    return "\n".join(lines)


async def process_upcoming_events(bot: Bot, cache: CalendarAlertCache) -> None:
    events = get_upcoming_events(minutes_ahead=CALENDAR_ALERT_MINUTES)
    if not events:
        logger.debug("다가오는 일정 없음")
        return

    new_events = cache.filter_new_events(events)
    if not new_events:
        logger.debug("이미 알림 전송된 이벤트뿐")
        return

    for event in new_events:
        message = format_event_message(event)
        try:
            await bot.send_message(chat_id=int(TELEGRAM_CHAT_ID), text=message)
            logger.info("Calendar 알림 전송: %s", event.get("summary"))
        except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
            logger.error("Calendar 알림 전송 실패: %s", exc)

        if slack.send_message(message):
            logger.info("Calendar Slack 알림 전송: %s", event.get("summary"))


async def monitor_loop() -> None:
    error = _validate_settings()
    if error:
        logger.error(error)
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    cache = CalendarAlertCache()

    logger.info(
        "Starting Calendar monitor loop (interval: %s sec, window: %s min)",
        POLL_INTERVAL,
        CALENDAR_ALERT_MINUTES,
    )

    while True:
        try:
            await process_upcoming_events(bot, cache)
        except Exception as exc:
            logger.error("Calendar monitor iteration 실패: %s", exc)
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        logger.info("Calendar monitor stopped at %s", datetime.now().isoformat())
