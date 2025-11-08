"""/gmail 명령 처리 핸들러."""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes

from backend.services.gmail import GmailService  # type: ignore

from ..utils.text_utils import format_email_entry


async def handle_gmail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    args_override: Optional[List[str]] = None,
) -> None:
    """최근 메일 조회 및 응답 전송."""

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
            try:
                korean_numbers = {
                    "하나": 1,
                    "일": 1,
                    "1": 1,
                    "둘": 2,
                    "이": 2,
                    "2": 2,
                    "셋": 3,
                    "삼": 3,
                    "3": 3,
                    "넷": 4,
                    "사": 4,
                    "4": 4,
                    "다섯": 5,
                    "오": 5,
                    "5": 5,
                    "여섯": 6,
                    "육": 6,
                    "6": 6,
                    "일곱": 7,
                    "칠": 7,
                    "7": 7,
                    "여덟": 8,
                    "팔": 8,
                    "8": 8,
                    "아홉": 9,
                    "구": 9,
                    "9": 9,
                    "열": 10,
                    "십": 10,
                    "10": 10,
                }
                if lowered in korean_numbers:
                    count = korean_numbers[lowered]
                else:
                    count = max(1, min(int(arg), 10))
            except ValueError:
                continue

    status_text = (
        f"📬 Gmail에서 최근 {'읽지 않은 ' if unread_only else ''}메일 {count}건을 확인하고 있습니다..."
    )
    await update.message.reply_text(status_text)

    gmail_service = GmailService()

    def fetch_emails() -> Tuple[bool, str, List[Dict[str, str]]]:
        try:
            if not gmail_service.authenticate():
                return (
                    False,
                    "Gmail 인증에 실패했습니다. OAuth 또는 서비스 계정 설정을 확인해주세요.",
                    [],
                )
            emails = gmail_service.fetch_email_details(
                max_results=count,
                mark_as_read=mark_as_read,
                unread_only=unread_only,
            )
            return True, "", emails
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"Gmail 정보를 가져오는 중 오류가 발생했습니다: {exc}", []

    success, error_message, emails = await asyncio.to_thread(fetch_emails)

    if not success:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ {error_message}")
        return

    if not emails and unread_only:
        await context.bot.send_message(
            chat_id=chat_id,
            text="읽지 않은 새로운 메일이 없습니다. 가장 최근 메일을 대신 보여드릴게요.",
        )

        def fetch_recent_emails() -> Tuple[bool, str, List[Dict[str, str]]]:
            return (
                True,
                "",
                gmail_service.fetch_email_details(
                    max_results=count,
                    mark_as_read=False,
                    unread_only=False,
                ),
            )

        success, error_message, emails = await asyncio.to_thread(fetch_recent_emails)
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
