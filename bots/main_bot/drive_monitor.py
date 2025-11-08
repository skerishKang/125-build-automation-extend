"""
Google Drive 폴더를 주기적으로 모니터링하여 새 파일이 감지되면 Telegram 채팅으로 알림을 보내는 스크립트.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from telegram import Bot

from backend.services.drive_sync import check_new_files
from backend.services import slack
from bots.shared.user_preferences import preference_store

logger = logging.getLogger("drive_monitor")
logging.basicConfig(level=logging.INFO)

TELEGRAM_CHAT_ID = os.getenv("DRIVE_ALERT_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
POLL_INTERVAL = int(os.getenv("DRIVE_POLL_INTERVAL", "60"))


def _validate_settings() -> Optional[str]:
    if not TELEGRAM_CHAT_ID:
        return "DRIVE_ALERT_CHAT_ID 환경 변수가 필요합니다."
    if not TELEGRAM_BOT_TOKEN:
        return "MAIN_BOT_TOKEN 환경 변수가 필요합니다."
    return None


async def process_new_files(bot: Bot) -> None:
    """신규 파일을 확인하고 알림을 전송합니다."""
    files = check_new_files()

    if not files:
        logger.debug("새로운 파일이 없습니다.")
        return

    slack_enabled = preference_store.get_preferences(str(TELEGRAM_CHAT_ID or ""))\
        .get("integrations", {}).get("slack", True)

    for file in files:
        name = file.get("name", "(이름 없음)")
        link = file.get("webViewLink") or file.get("webContentLink", "")
        created = file.get("createdTime", "")
        modified = file.get("modifiedTime", "")

        message = [
            "📂 Google Drive에 새 파일이 업로드되었어요!",
            f"- 이름: {name}",
        ]

        if created:
            message.append(f"- 생성: {created}")
        if modified and modified != created:
            message.append(f"- 수정: {modified}")
        if link:
            message.append(f"- 링크: {link}")

        text = "\n".join(message)

        try:
            await bot.send_message(chat_id=int(TELEGRAM_CHAT_ID), text=text)
            logger.info("Sent Drive alert for %s", name)
        except Exception as exc:  # pragma: no cover - 네트워크 오류 방어
            logger.error("Failed to send Drive alert: %s", exc)

        if slack_enabled and slack.send_message(text):
            logger.info("Sent Drive alert to Slack for %s", name)


async def monitor_loop() -> None:
    """주기적으로 Drive 변화를 체크합니다."""
    error = _validate_settings()
    if error:
        logger.error(error)
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    logger.info("Starting Drive monitor loop (interval: %s seconds)", POLL_INTERVAL)

    while True:
        try:
            await process_new_files(bot)
        except Exception as exc:
            logger.error("Drive monitor iteration failed: %s", exc)
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(monitor_loop())
    except KeyboardInterrupt:
        logger.info("Drive monitor stopped at %s", datetime.now().isoformat())
