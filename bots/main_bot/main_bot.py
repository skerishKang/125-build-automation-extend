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
from datetime import datetime
from typing import Any, Dict, Optional

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, Bot
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackContext, filters

from bots.shared.redis_utils import BotMessenger, REDIS_ENABLED  # type: ignore
from bots.shared.gemini_client import GeminiAnalyzer  # type: ignore
from bots.shared.telegram_utils import (  # type: ignore
    is_text_file,
    is_document_file,
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

# Global state
active_tasks: Dict[str, Dict] = {}  # chat_id -> task_info
user_sessions: Dict[str, Dict] = {}  # user_id -> session_info
pending_results: Dict[str, Dict[str, Any]] = {}  # chat_id -> {event, result}

# Initialize messenger
messenger = BotMessenger("main_bot")
gemini = GeminiAnalyzer(GEMINI_API_KEY)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    name = user.first_name or "사용자"

    welcome_message = f"""
안녕하세요 {name}님! 메인봇이에요!

저는 전문봇들과 협력하는 메인봇입니다!

사용 가능한 기능:
• 자유 대화 (Gemini AI)
• 문서 분석 (PDF, DOCX, TXT 등)
• 음성 처리 (OGG, MP3, WAV 등)
• 이미지 분석 (JPG, PNG 등)

명령어:
• /help - 도움말 보기
• /status - 봇 상태 확인
• /bots - 전문봇 목록

파일 업로드:
문서, 이미지, 음성 파일을 업로드하면 전문봇이 분석해드립니다!

developed by PadiemAI, LimoneAI
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
• /status - 현재 봇 상태
• /bots - 전문봇 상태 확인

사용 팁
• 여러 파일을 동시에 업로드 가능
• 파일 크기는 최대 50MB까지 지원
• 분석 중에도 다른 대화 계속 가능!
    """

    await update.message.reply_text(help_text)


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    chat_id = str(update.effective_chat.id)

    # Get task status
    task_count = len(active_tasks)
    active_task_info = ""

    if chat_id in active_tasks:
        task = active_tasks[chat_id]
        active_task_info = f"""
[STATS] **현재 작업:**
• 타입: {task.get('type', 'N/A')}
• 상태: {task.get('status', 'N/A')}
• 시작: {task.get('start_time', 'N/A')}
"""

    status_text = f"""
메인봇 상태

연결 상태:
• 메인봇: 실행 중
• Redis: {REDIS_HOST}:{REDIS_PORT}
• Gemini AI: {'활성' if GEMINI_API_KEY else '비활성'}

작업 현황:
• 활성 작업: {task_count}개
{active_task_info}

전문봇:
• 문서봇: 준비 완료
• 오디오봇: 준비 완료
• 사진봇: 준비 완료
    """

    await update.message.reply_text(status_text)


async def handle_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bots command - Check specialized bot status"""
    status_text = """
전문봇 상태

문서봇
• 역할: PDF, DOCX, TXT 등 문서 전문 분석
• 기능: 텍스트 추출, AI 분석, 요약
• 상태: 대기 중

오디오봇
• 역할: OGG, MP3, WAV 등 음성 전문 처리
• 기능: 음성 인식(Whisper), AI 요약
• 상태: 대기 중

사진봇
• 역할: JPG, PNG 등 이미지 전문 분석
• 기능: 이미지 설명, OCR, AI 분석
• 상태: 대기 중

사용법:
메인봇에 파일을 업로드하면 해당 전문봇이 자동으로 처리합니다!
    """

    await update.message.reply_text(status_text)


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

    # Send typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Use Gemini to generate response
    response = gemini.analyze_text(text)

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


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads"""
    doc = update.message.document
    if not doc:
        return

    chat_id = str(update.effective_chat.id)
    file_name = doc.file_name or "document"
    file_size = doc.file_size or 0

    logger.info(f"Document upload: {file_name} ({file_size} bytes)")

    # Check if it's a document
    if not is_document_file(file_name) and not is_text_file(file_name):
        await update.message.reply_text(
            f"[WARN] 지원하지 않는 파일 형식입니다: {file_name}\n"
            f"지원 형식: PDF, DOCX, TXT, CSV 등"
        )
        return

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        await update.message.reply_text(
            f"[WARN] 파일이 너무 큽니다 (최대 50MB)\n"
            f"현재 크기: {file_size / (1024*1024):.1f}MB"
        )
        return

    # Acknowledge receipt
    await update.message.reply_text(
        f"문서 접수!\n"
        f"파일: {file_name}\n"
        f"크기: {file_size / 1024:.1f}KB\n"
        f"문서봇이 분석 중입니다..."
    )

    # Store task info
    active_tasks[chat_id] = {
        "type": "document",
        "status": "processing",
        "file_name": file_name,
        "file_id": doc.file_id,
        "start_time": datetime.now().strftime("%H:%M:%S")
    }

    # Send to document bot
    messenger.publish_task("document", {
        "chat_id": chat_id,
        "file_data": {
            "file_id": doc.file_id,
            "file_name": file_name,
            "file_size": file_size
        },
        "user_id": str(update.effective_user.id)
    })

    logger.info(f"Sent document task to document bot for chat {chat_id}")

    result_payload = await wait_for_result(chat_id, timeout=180)

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏰ 문서 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요."
        )
        active_tasks.pop(chat_id, None)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    voice = update.message.voice
    if not voice:
        return

    chat_id = str(update.effective_chat.id)
    duration = voice.duration or 0

    logger.info(f"Voice message: {duration}s")

    # Check if it's audio
    if not voice.mime_type or not voice.mime_type.startswith('audio/'):
        await update.message.reply_text(
            "[WARN] 오디오 파일이 아닙니다."
        )
        return

    # Check duration (max 5 minutes)
    max_duration = 5 * 60
    if duration > max_duration:
        await update.message.reply_text(
            f"[WARN] 음성이 너무 깁니다 (최대 5분)\n"
            f"현재 길이: {duration // 60}분 {duration % 60}초"
        )
        return

    # Acknowledge
    await update.message.reply_text(
        f"음성 접수!\n"
        f"길이: {duration // 60}분 {duration % 60}초\n"
        f"오디오봇이 처리 중입니다..."
    )

    # Store task info
    active_tasks[chat_id] = {
        "type": "audio",
        "status": "processing",
        "duration": duration,
        "file_id": voice.file_id,
        "start_time": datetime.now().strftime("%H:%M:%S")
    }

    # Send to audio bot
    messenger.publish_task("audio", {
        "chat_id": chat_id,
        "voice_data": {
            "file_id": voice.file_id,
            "duration": duration,
            "mime_type": voice.mime_type
        },
        "user_id": str(update.effective_user.id)
    })

    logger.info(f"Sent voice task to audio bot for chat {chat_id}")

    result_payload = await wait_for_result(chat_id, timeout=180)

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏰ 음성 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요."
        )
        active_tasks.pop(chat_id, None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads"""
    photo = update.message.photo[-1]  # Get highest resolution
    if not photo:
        return

    chat_id = str(update.effective_chat.id)
    file_id = photo.file_id

    logger.info(f"Photo upload: {file_id}")

    # Acknowledge
    await update.message.reply_text(
        f"이미지 접수!\n"
        f"사진봇이 분석 중입니다..."
    )

    # Store task info
    active_tasks[chat_id] = {
        "type": "image",
        "status": "processing",
        "file_id": file_id,
        "start_time": datetime.now().strftime("%H:%M:%S")
    }

    # Send to image bot
    messenger.publish_task("image", {
        "chat_id": chat_id,
        "image_data": {
            "file_id": file_id
        },
        "user_id": str(update.effective_user.id)
    })

    logger.info(f"Sent image task to image bot for chat {chat_id}")

    result_payload = await wait_for_result(chat_id, timeout=120)

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏰ 이미지 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요."
        )
        active_tasks.pop(chat_id, None)


async def _process_result_payload(bot: Bot, payload: Dict[str, Any]):
    """Process a single result payload coming from Redis."""
    chat_id = str(payload.get("chat_id") or "")
    result = payload.get("result", {})
    bot_name = payload.get("bot_name", "unknown")

    if not chat_id:
        logger.warning("Result payload missing chat_id: %s", payload)
        return

    if chat_id not in active_tasks:
        logger.warning("Received result for inactive chat %s", chat_id)
        return

    try:
        if bot_name == "document_bot":
            await send_document_result(bot, chat_id, result)
        elif bot_name == "audio_bot":
            await send_audio_result(bot, chat_id, result)
        elif bot_name == "image_bot":
            await send_image_result(bot, chat_id, result)
        else:
            logger.warning("Unknown bot_name in result payload: %s", bot_name)
            await bot.send_message(
                chat_id=int(chat_id),
                text="처리 결과를 받았지만 어떤 전문봇에서 왔는지 확인할 수 없어요."
            )
    finally:
        active_tasks.pop(chat_id, None)
        logger.info("Completed task for chat %s", chat_id)


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
            timeout=0.2,
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
                    chat_id = str(payload.get("chat_id") or "")
                    if chat_id in pending_results:
                        pending_results[chat_id]["result"] = payload
                        pending_results[chat_id]["event"].set()
                    else:
                        await _process_result_payload(context.bot, payload)
                else:
                    logger.warning("Unexpected payload type from Redis: %r", payload)

            message = await asyncio.to_thread(
                messenger.pubsub.get_message,
                ignore_subscribe_messages=True,
                timeout=0.0,
            )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Result listener error: %s", exc)


async def wait_for_result(chat_id: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """Wait for a result payload from specialized bots."""
    event = asyncio.Event()
    pending_results[chat_id] = {"event": event, "result": None}

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        return pending_results.get(chat_id, {}).get("result")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for result for chat %s", chat_id)
        return None
    finally:
        pending_results.pop(chat_id, None)


async def send_document_result(bot: Bot, chat_id: str, result: Dict):
    """Send document analysis result to user"""
    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=f"문서 분석 완료!\n\n{result.get('text', 'N/A')}\n\n요약:\n{result.get('summary', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"Error sending document result: {e}")


async def send_audio_result(bot: Bot, chat_id: str, result: Dict):
    """Send audio transcription result to user"""
    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=f"음성 처리 완료!\n\n전사:\n{result.get('transcription', 'N/A')}\n\n요약:\n{result.get('summary', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"Error sending audio result: {e}")


async def send_image_result(bot: Bot, chat_id: str, result: Dict):
    """Send image analysis result to user"""
    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=f"이미지 분석 완료!\n\n설명:\n{result.get('description', 'N/A')}\n\n분석:\n{result.get('analysis', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"Error sending image result: {e}")


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

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Start bot
    print("[OK] Bot is running...")
    print("Press Ctrl+C to stop")

    if REDIS_ENABLED and messenger.pubsub:
        messenger.pubsub.subscribe("main_bot_results")
        application.job_queue.run_repeating(
            poll_result_messages,
            interval=1.0,
            name="result_listener",
        )
        logger.info("Result listener scheduled via job queue")
    else:
        logger.info("Redis disabled or unavailable; skipping result listener")

    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\nBYE Shutting down...")
    finally:
        messenger.close()


if __name__ == "__main__":
    import asyncio
    main()
