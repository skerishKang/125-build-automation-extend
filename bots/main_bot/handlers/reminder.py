"""리마인더 관련 명령 핸들러."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Optional

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from ..utils.datetime_utils import parse_relative_date_time

_REMINDER_KEYWORD_PATTERN = re.compile(r"(리마인드|리마인더|알림|알려줘|remind)", re.IGNORECASE)


async def handle_reminder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    original_text: str,
) -> None:
    """자연어 리마인더 요청 처리."""
    parsed = parse_relative_date_time(original_text)
    if not parsed:
        await update.message.reply_text(
            "⏰ 리마인더 시간을 이해하지 못했어요.\n"
            "`/remind 10m 회의 준비` 처럼 명령어로 알려주시면 정확히 예약할 수 있어요."
        )
        return

    due_time = parsed["start"]
    message_text = _sanitize_message(original_text)
    if not message_text:
        message_text = "지금 말씀하신 내용을 다시 알려드릴게요!"

    await _schedule_reminder(update, context, due_time, message_text)


async def handle_reminder_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """`/remind` 명령 처리.

    사용 예시:
      /remind 10m 회의 준비
      /remind 1h30m 점심예약 전화
    """
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "사용법: `/remind <시간> [메시지]`\n"
            "예) `/remind 10m 회의 준비`, `/remind 1h 점심 예약`",
            parse_mode="Markdown",
        )
        return

    now = datetime.now().astimezone()
    duration, rest = _parse_duration_and_message(args)

    if duration is None:
        command_text = " ".join(args)
        parsed = parse_relative_date_time(command_text)
        if not parsed:
            await update.message.reply_text(
                "⏰ 시간을 이해하지 못했어요. `10m`, `2h`, `내일 오후 3시` 처럼 알려주세요."
            )
            return
        due_time = parsed["start"]
        message_text = _sanitize_message(command_text)
    else:
        due_time = now + duration
        message_text = rest or "리마인더 알림입니다!"

    await _schedule_reminder(update, context, due_time, message_text)


async def _schedule_reminder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    due_time: datetime,
    message_text: str,
) -> None:
    if context.job_queue is None:
        await update.message.reply_text("현재 리마인더 기능을 사용할 수 없습니다 (JobQueue 미활성화).")
        return

    now = datetime.now().astimezone()
    delay = (due_time - now).total_seconds()
    if delay < 0:
        delay = 0
    if delay < 5:
        delay = 5  # 최소 5초 후로 조정

    job_name = (
        f"reminder-{update.effective_chat.id}-{update.effective_user.id}-"
        f"{datetime.now().timestamp()}"
    )
    context.job_queue.run_once(
        reminder_job,
        when=delay,
        chat_id=update.effective_chat.id,
        name=job_name,
        data={"message": message_text},
    )

    due_time_display = (now + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(
        "⏰ 리마인더를 등록했어요!\n"
        f"- 시간: {due_time_display}\n"
        f"- 메시지: {message_text}"
    )


async def reminder_job(context: CallbackContext) -> None:
    data = context.job.data or {}
    message_text = data.get("message", "⏰ 리마인더 알림입니다!")
    await context.bot.send_message(chat_id=context.job.chat_id, text=f"⏰ {message_text}")


def _parse_duration_and_message(args: List[str]) -> tuple[Optional[timedelta], str]:
    if not args:
        return None, ""

    possible_duration = args[0]
    duration = _parse_duration_token(possible_duration)
    if duration is None:
        return None, " ".join(args)

    message = " ".join(args[1:]).strip()
    return duration, message


_DURATION_PATTERN = re.compile(
    r"^(?P<value>\d+)(?P<unit>ms|s|sec|secs|초|m|min|mins|분|h|hr|hrs|hour|hours|시간|d|day|days|일)$",
    re.IGNORECASE,
)


def _parse_duration_token(token: str) -> Optional[timedelta]:
    match = _DURATION_PATTERN.match(token)
    if not match:
        return None

    value = int(match.group("value"))
    unit = match.group("unit").lower()

    if unit in {"ms"}:
        seconds = value / 1000
    elif unit in {"s", "sec", "secs", "초"}:
        seconds = value
    elif unit in {"m", "min", "mins", "분"}:
        seconds = value * 60
    elif unit in {"h", "hr", "hrs", "hour", "hours", "시간"}:
        seconds = value * 60 * 60
    elif unit in {"d", "day", "days", "일"}:
        seconds = value * 60 * 60 * 24
    else:
        return None

    return timedelta(seconds=seconds)


def _sanitize_message(text: str) -> str:
    cleaned = _REMINDER_KEYWORD_PATTERN.sub("", text)
    cleaned = cleaned.replace("/remind", "")
    return cleaned.strip()
