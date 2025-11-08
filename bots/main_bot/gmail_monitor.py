"""
Gmail을 주기적으로 폴링하여 새 메일을 감지하고 텔레그램으로 알림을 보내는 모니터 스크립트.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

from backend.services.gmail import GmailService
from bots.shared.gemini_client import GeminiAnalyzer
from bots.shared.telegram_utils import build_bot
from bots.shared.user_preferences import preference_store

logger = logging.getLogger("gmail_monitor")
logging.basicConfig(level=logging.INFO)

TELEGRAM_CHAT_ID = os.getenv("GMAIL_ALERT_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
POLL_INTERVAL = int(os.getenv("GMAIL_MONITOR_INTERVAL", "300"))
GMAIL_UNREAD_ONLY = os.getenv("GMAIL_UNREAD_ONLY", "true").lower() == "true"
GMAIL_MARK_AS_READ = os.getenv("GMAIL_MARK_AS_READ", "false").lower() == "true"
MAX_EMAILS_PER_CYCLE = int(os.getenv("GMAIL_MAX_EMAILS", "5"))


def _validate_settings() -> Optional[str]:
    if not TELEGRAM_CHAT_ID:
        return "GMAIL_ALERT_CHAT_ID 환경 변수가 필요합니다."
    if not TELEGRAM_BOT_TOKEN:
        return "MAIN_BOT_TOKEN 환경 변수가 필요합니다."
    return None


def summarize_email(email: dict, gemini: GeminiAnalyzer) -> str:
    prompt = (
        "다음 이메일을 한국어로 간결하게 정리해주세요.\n"
        "형식:\n"
        "1) 핵심 요약 (2-3문장)\n"
        "2) 중요도 (높음/보통/낮음 중 하나)\n"
        "3) 필요한 액션이 있다면 제안\n\n"
        f"보낸사람: {email.get('sender', '알 수 없음')}\n"
        f"제목: {email.get('subject', '제목 없음')}\n"
        f"내용: {email.get('body', '')}"
    )
    summary = gemini.analyze_text(prompt)
    return summary or "요약 생성 실패"


def format_email_message(email: dict, summary: str) -> str:
    lines: List[str] = [
        "새 메일이 도착했습니다!",
        f"- 보낸사람: {email.get('sender', '알 수 없음')}",
        f"- 제목: {email.get('subject', '제목 없음')}",
    ]

    date_str = email.get('date')
    if date_str:
        lines.append(f"- 시간: {date_str}")

    link = email.get('link')
    if link:
        lines.append(f"- 링크: {link}")

    lines.append("\n AI 요약:\n" + summary)
    return "\n".join(lines)


def fetch_new_emails(service: GmailService) -> List[dict]:
    details = service.fetch_email_details(
        max_results=MAX_EMAILS_PER_CYCLE,
        mark_as_read=GMAIL_MARK_AS_READ,
        unread_only=GMAIL_UNREAD_ONLY,
    )

    new_emails = []
    for item in details:
        email_id = item.get("id")
        if email_id and email_id not in service.processed_emails:
            service.processed_emails.add(email_id)
            new_emails.append(item)

    if new_emails:
        service.save_processed_emails()

    return new_emails


async def process_new_emails(bot: Bot, gemini: GeminiAnalyzer, service: GmailService) -> None:
    emails = fetch_new_emails(service)
    if not emails:
        logger.debug("새 이메일 없음")
        return

    prefs = preference_store.get_preferences(TELEGRAM_CHAT_ID or "")
    slack_enabled = prefs.get("integrations", {}).get("slack", True)

    for email in emails:
        summary = summarize_email(email, gemini)
        message = format_email_message(email, summary)
        try:
            await bot.send_message(chat_id=int(TELEGRAM_CHAT_ID), text=message)
            logger.info("Gmail 알림 전송: %s", email.get('subject'))
        except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
            logger.error("Gmail 알림 전송 실패: %s", exc)

        if slack_enabled and slack.send_message(message):
            logger.info("Gmail Slack 알림 전송: %s", email.get('subject'))


async def monitor_loop() -> None:
    error = _validate_settings()
    if error:
        logger.error(error)
        return

    service = GmailService()
    if not service.authenticate():
        logger.error("Gmail 인증 실패")
        return

    bot = build_bot(TELEGRAM_BOT_TOKEN)
    gemini = GeminiAnalyzer()

    logger.info(
        "Starting Gmail monitor loop (interval: %s sec, unread_only=%s, mark_as_read=%s)",
        POLL_INTERVAL,
        GMAIL_UNREAD_ONLY,
        GMAIL_MARK_AS_READ,
    )

    while True:
        try:
            await process_new_emails(bot, gemini, service)
        except Exception as exc:
            logger.error("Gmail monitor iteration 실패: %s", exc)
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        logger.info("Gmail monitor stopped at %s", datetime.now().isoformat())
