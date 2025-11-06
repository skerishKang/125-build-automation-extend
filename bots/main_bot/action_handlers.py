"""
Action Handlers - Post-processing hooks for document bot results.
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple

from telegram import Bot

logger = logging.getLogger("action_handlers")

ACTION_LABELS: Dict[str, str] = {
    "none": "아무 작업하지 않기",
    "drive": "Google Drive에 저장",
    "notion": "Notion 페이지 생성"
}


async def execute_document_action(action: str, bot: Bot, chat_id: str, result: Dict) -> Tuple[str, str]:
    """
    Execute the selected follow-up action.

    Returns a tuple of (action_code, human_readable_message) so the caller can
    relay what happened back to the user.
    """
    action = (action or "none").lower()

    if action == "drive":
        # Placeholder implementation. Replace with real Drive API integration.
        logger.info("Simulating Drive upload for chat %s (file: %s)", chat_id, result.get("file_name"))
        message = "📂 문서 요약을 Google Drive에 저장했다고 가정할게요. (샘플 코드)"
    elif action == "notion":
        # Placeholder for Notion automation.
        logger.info("Simulating Notion export for chat %s (file: %s)", chat_id, result.get("file_name"))
        message = "🗂️ Notion 페이지를 생성했다고 가정할게요. (샘플 코드)"
    else:
        action = "none"
        message = "처리 결과를 저장하지 않고 마무리했어요."

    try:
        await bot.send_message(chat_id=int(chat_id), text=message)
    except Exception as exc:
        logger.error("Failed to send action confirmation message: %s", exc)

    return action, message

