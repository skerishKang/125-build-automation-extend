"""Gmail command handlers extracted from the monolithic runtime module."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from typing import Any


def _ensure_backend_path():
    backend_path = os.path.join(os.path.dirname(__file__), "..", "..")
    backend_path = os.path.abspath(backend_path)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


async def handle_gmail_on(runtime: Any, update, context):
    """Handle /gmail_on command - Start Gmail monitoring."""
    state = runtime.gmail_monitoring_state
    reply_text = runtime.reply_text
    logger = runtime.logger

    if state["enabled"]:
        await reply_text(
            update,
            "🟡 **Gmail 감시가 이미 실행 중이에요!**\n"
            f"- 현재까지 {state['total_emails']}개 메일 처리됨\n"
            "- `/gmail_status`로 상세 상태 확인",
        )
        return

    test_msg = await reply_text(update, "📧 Gmail 연결 테스트 중...")

    try:
        _ensure_backend_path()
        from backend.services.gmail import GmailService  # noqa: WPS433

        gmail_service = GmailService()
        if not gmail_service.authenticate():
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=test_msg.message_id,
                text=(
                    "❌ Gmail 인증 실패. gmail_credentials.json 파일을 확인해주세요.\n\n"
                    "📋 설정 방법:\n"
                    "1. https://console.cloud.google.com/ 접속\n"
                    "2. Gmail API 활성화\n"
                    "3. OAuth 2.0 클라이언트 ID 생성\n"
                    "4. 다운로드한 파일을 gmail_credentials.json으로 저장"
                ),
            )
            return

        gmail_service.get_recent_emails(max_results=1)

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text="✅ Gmail 연결 성공! 감시를 시작합니다...",
        )

        state["enabled"] = True
        state["total_emails"] = 0
        state["start_time"] = datetime.now().isoformat()
        runtime.start_gmail_monitoring()

        await asyncio.sleep(1)

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text=(
                "🟢 **Gmail 실시간 감시 시작!**\n\n"
                "📋 **감시 설정**:\n"
                "- 확인 주기: 5분마다\n"
                "- 대상: 읽지 않은 메일만\n"
                "- AI 요약: Gemini 2.5 Flash\n"
                "- 즉시 텔레그램 알림\n\n"
                "💡 **명령어**:\n"
                "- `/gmail_off` - 감시 중지\n"
                "- `/gmail_status` - 상태 확인\n"
                "- `/gmail_list` - 최근 메일 목록"
            ),
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Gmail start error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=test_msg.message_id,
            text=f"❌ Gmail 연결 실패: {str(exc)[:100]}",
        )


async def handle_gmail_off(runtime: Any, update, context):
    state = runtime.gmail_monitoring_state
    reply_text = runtime.reply_text

    if not state["enabled"]:
        await reply_text(update, "🔴 Gmail 감시가 이미 중지되어 있어요!")
        return

    state["enabled"] = False
    total_processed = state.get("total_emails", 0)

    stop_message = (
        "📪 **Gmail 감시 중지됨**\n\n"
        "📊 **이번 세션 통계**:\n"
        f"- 처리된 메일: {total_processed}개\n"
        f"- 감시 시간: {state.get('start_time', '확인 불가')}부터\n\n"
        "💡 **재시작하려면**:\n"
        "- `/gmail_on` - 감시 다시 시작\n"
        "- `/gmail_list` - 수동으로 메일 목록 확인"
    )

    await reply_text(update, stop_message)


async def handle_gmail_status(runtime: Any, update, context):
    state = runtime.gmail_monitoring_state
    reply_text = runtime.reply_text
    logger = runtime.logger

    status_icon = "🟢" if state["enabled"] else "🔴"
    status_text = "실행 중" if state["enabled"] else "중지됨"

    last_check = state.get("last_check", "없음")
    total_emails = state.get("total_emails", 0)

    if state["enabled"]:
        try:
            _ensure_backend_path()
            from backend.services.gmail import GmailService  # noqa: WPS433

            gmail_service = GmailService()
            unread_count = (
                gmail_service.get_unread_count() if gmail_service.authenticate() else "확인 불가"
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Gmail unread count failed: %s", exc)
            unread_count = "확인 불가"
    else:
        unread_count = "감시 중지됨"

    status_message = (
        "📊 **Gmail 감시 상태**\n\n"
        f"{status_icon} **상태**: {status_text}\n"
        f"🕒 **마지막 확인**: {last_check}\n"
        f"📧 **처리된 메일**: {total_emails}개\n"
        f"🔵 **현재 받은편지함**: {unread_count}개\n\n"
        "💡 **사용 가능한 명령어**:\n"
        "- `/gmail_on` - 감시 시작\n"
        "- `/gmail_off` - 감시 중지\n"
        "- `/gmail_list` - 최근 메일 목록"
    )

    await reply_text(update, status_message)


async def handle_gmail_list(runtime: Any, update, context):
    reply_text = runtime.reply_text
    logger = runtime.logger

    ack_msg = await reply_text(update, "📧 최근 메일 목록 가져오는 중...")

    try:
        _ensure_backend_path()
        from backend.services.gmail import GmailService  # noqa: WPS433

        gmail_service = GmailService()
        if not gmail_service.authenticate():
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text="❌ Gmail 인증 실패. 먼저 `/gmail_on`으로 인증해주세요.",
            )
            return

        recent_emails = gmail_service.get_recent_emails(max_results=20)

        if not recent_emails:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=ack_msg.message_id,
                text="📪 읽지 않은 메일이 없어요.",
            )
            return

        email_list = []
        for index, email_info in enumerate(recent_emails[:10], start=1):
            email_content = gmail_service.get_email_content(email_info['id'])
            if email_content:
                is_unread = "🔵" if 'UNREAD' in email_info.get('labelIds', []) else "⚪"
                email_list.append(
                    (
                        f"{index}. {is_unread} **{email_content['subject'][:40]}**\n"
                        f"   👤 {email_content['sender'][:30]}\n"
                        f"   🕒 {email_content['date'][:16]}"
                    )
                )

        final_message = (
            "📋 **최근 Gmail 목록** (최대 10개)\n\n"
            f"{chr(10).join(email_list)}\n\n"
            "📊 **요약**:\n"
            f"- 전체 확인된 메일: {len(recent_emails)}개\n"
            "- 🔵 읽지 않은 메일  ⚪ 읽은 메일\n"
            "- `/gmail_on`으로 실시간 감시 시작 가능"
        )

        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=final_message,
        )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Gmail list error: %s", exc)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=ack_msg.message_id,
            text=f"❌ Gmail 목록 조회 중 오류가 발생했어요: {str(exc)[:100]}",
        )
