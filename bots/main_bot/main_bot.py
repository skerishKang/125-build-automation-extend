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

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext,
    filters,
)

from bots.shared.redis_utils import BotMessenger, REDIS_ENABLED  # type: ignore
from bots.shared.gemini_client import GeminiAnalyzer  # type: ignore
from bots.shared.user_preferences import preference_store, DEFAULT_PREFERENCES  # type: ignore
from bots.main_bot.action_handlers import (  # type: ignore
    execute_document_action,
    ACTION_LABELS,
)
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


def estimate_processing_time(task_type: str, file_info: Dict) -> int:
    """Estimate processing time in seconds based on task type and file info."""
    if task_type == "audio":
        duration = file_info.get("duration", 60)
        return int(duration * 2.5) + 30

    if task_type == "document":
        file_name = (file_info.get("file_name") or "").lower()
        file_size = file_info.get("file_size", 0)

        if file_name.endswith(".pdf"):
            estimated_pages = (file_size / 1024 / 1024) * 20
            return int(estimated_pages * 1.5) + 30
        if file_name.endswith(".docx"):
            return 60
        if file_name.endswith(".txt"):
            return 30
        if file_name.endswith(".xlsx") or file_name.endswith(".csv"):
            return 90
        return 60

    if task_type == "image":
        return 30

    return 60


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds}초"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if remaining_seconds > 0:
        return f"{minutes}분 {remaining_seconds}초"
    return f"{minutes}분"


async def send_progress_updates(
    bot: Bot,
    chat_id: int,
    task_type: str,
    estimated_time: int,
    cancel_event: asyncio.Event,
) -> Optional[int]:
    """Send progress updates every minute until the task completes."""
    emoji_map = {"audio": "🎤", "document": "📄", "image": "🖼️"}
    emoji = emoji_map.get(task_type, "⚙️")

    initial_text = f"{emoji} 처리 중!\n⏱️ 예상 시간: ~{format_duration(estimated_time)}"
    message = await bot.send_message(chat_id=chat_id, text=initial_text)
    message_id = message.message_id

    start_time = asyncio.get_event_loop().time()
    update_interval = 60

    while not cancel_event.is_set():
        try:
            await asyncio.wait_for(cancel_event.wait(), timeout=update_interval)
            break
        except asyncio.TimeoutError:
            elapsed = int(asyncio.get_event_loop().time() - start_time)
            if estimated_time > 0:
                progress_percent = min(99, int((elapsed / estimated_time) * 100))
                if progress_percent > 0:
                    remaining = int((estimated_time * (100 - progress_percent)) / progress_percent)
                else:
                    remaining = estimated_time
            else:
                progress_percent = 50
                remaining = 0

            filled = int(progress_percent / 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_text = (
                f"{emoji} 처리 중... {progress_percent}%\n"
                f"{bar}\n"
                f"⏱️ 경과: {format_duration(elapsed)}"
            )
            if remaining > 0:
                progress_text += f" / 남은 시간: ~{format_duration(remaining)}"

            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=progress_text,
                )
            except Exception as exc:
                logger.warning("Failed to update progress message: %s", exc)

    return message_id

# Global state
active_tasks: Dict[str, Dict] = {}  # chat_id -> task_info
user_sessions: Dict[str, Dict] = {}  # user_id -> session_info
pending_results: Dict[str, Dict[str, Any]] = {}  # chat_id -> {event, result}
document_followups: Dict[str, Dict[str, Any]] = {}  # chat_id -> last document result

MODE_LABELS = {
    "ask": "대화형 모드 (항상 물어보기)",
    "auto": "자동 실행 모드",
    "skip": "요약만 받고 건너뛰기",
}


def build_settings_message(prefs: Dict[str, str]) -> str:
    """Create user-facing summary of current automation preferences."""
    mode_label = MODE_LABELS.get(prefs.get("mode", ""), "미설정")
    action_code = prefs.get("default_action", "none")
    action_label = ACTION_LABELS.get(action_code, "없음")

    lines = [
        "⚙️ 현재 하이브리드 자동화 설정",
        f"• 모드: {mode_label}",
        f"• 기본 후속 작업: {action_label}",
        "",
        "원하는 옵션을 선택해 설정을 변경할 수 있습니다.",
    ]
    return "\n".join(lines)


def build_settings_keyboard(prefs: Dict[str, str]) -> InlineKeyboardMarkup:
    """Return inline keyboard for settings adjustments."""
    mode_buttons = [
        InlineKeyboardButton("대화형 모드", callback_data="pref_mode|ask"),
        InlineKeyboardButton("자동 실행", callback_data="pref_mode|auto"),
        InlineKeyboardButton("요약만", callback_data="pref_mode|skip"),
    ]

    action_buttons = [
        InlineKeyboardButton("Drive 저장", callback_data="pref_action|drive"),
        InlineKeyboardButton("Notion 생성", callback_data="pref_action|notion"),
        InlineKeyboardButton("기본값 없음", callback_data="pref_action|none"),
    ]

    return InlineKeyboardMarkup([mode_buttons, action_buttons])


def build_document_action_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for document follow-up actions."""
    once_row = [
        InlineKeyboardButton("Drive 저장", callback_data="doc_action|once|drive"),
        InlineKeyboardButton("Notion 생성", callback_data="doc_action|once|notion"),
        InlineKeyboardButton("건너뛰기", callback_data="doc_action|once|none"),
    ]
    auto_row = [
        InlineKeyboardButton("항상 Drive", callback_data="doc_action|auto|drive"),
        InlineKeyboardButton("항상 Notion", callback_data="doc_action|auto|notion"),
        InlineKeyboardButton("항상 묻기", callback_data="doc_action|ask|none"),
    ]
    extra_row = [
        InlineKeyboardButton("항상 건너뛰기", callback_data="doc_action|skip|none"),
        InlineKeyboardButton("설정 열기", callback_data="pref_open|doc"),
    ]

    return InlineKeyboardMarkup([once_row, auto_row, extra_row])


async def prompt_document_followup(bot: Bot, chat_id: str) -> None:
    """Send follow-up prompt with inline options."""
    message = (
        "📤 후속 작업을 선택해주세요!\n"
        "1️⃣ Drive 저장\n"
        "2️⃣ Notion 보고서 생성\n"
        "3️⃣ 아무것도 안 함\n"
        "\n"
        "🔁 \"항상\" 버튼을 선택하면 다음부터 자동으로 처리합니다."
    )

    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=message,
            reply_markup=build_document_action_keyboard(),
        )
    except Exception as exc:
        logger.error("Failed to send document follow-up prompt: %s", exc)


async def apply_preferences_to_pending_document(bot: Bot, chat_id: str, prefs: Dict[str, str]) -> None:
    """Apply current preferences to any pending document result."""
    result_payload = document_followups.get(chat_id)
    if not result_payload:
        return

    mode = prefs.get("mode", DEFAULT_PREFERENCES["mode"])
    action = prefs.get("default_action", DEFAULT_PREFERENCES["default_action"])

    if mode == "auto" and action != "none":
        action_label = ACTION_LABELS.get(action, action)
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"🔁 자동 실행 설정에 따라 \"{action_label}\" 작업을 진행합니다.",
            )
        except Exception as exc:
            logger.error("Failed to announce auto action (settings): %s", exc)
        await execute_document_action(action, bot, chat_id, result_payload)
        document_followups.pop(chat_id, None)
    elif mode == "skip":
        try:
            await bot.send_message(
                chat_id=int(chat_id),
                text="요약만 전달하고 후속 작업은 건너뛰겠습니다.",
            )
        except Exception as exc:
            logger.error("Failed to send skip confirmation: %s", exc)
        document_followups.pop(chat_id, None)
    else:
        await prompt_document_followup(bot, chat_id)
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


async def handle_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command for automation preferences."""
    chat_id = str(update.effective_chat.id)
    prefs = preference_store.get_preferences(chat_id)

    await update.message.reply_text(
        build_settings_message(prefs),
        reply_markup=build_settings_keyboard(prefs),
    )


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
    filename = doc.file_name or "document"
    file_size = doc.file_size or 0

    logger.info(f"Document upload: {filename} ({file_size} bytes)")

    if not is_document_file(filename) and not is_text_file(filename):
        await update.message.reply_text(
            f"⚠️ WARN: {filename}\n지원 형식: PDF, DOCX, TXT, CSV"
        )
        return

    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        await update.message.reply_text(
            f"⚠️ WARN: 파일이 너무 큽니다 (최대 50MB)\n현재 크기: {file_size / (1024*1024):.1f}MB"
        )
        return

    await update.message.reply_text(
        f"📄 문서를 받았습니다!\n파일: {filename}\n크기: {file_size / 1024:.1f}KB"
    )

    active_tasks[chat_id] = {
        "type": "document",
        "status": "processing",
        "file_name": filename,
        "file_id": doc.file_id,
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(doc.file_id)
        import tempfile
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"doc_{chat_id}_{filename}")
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded document to {file_path}")
    except Exception as exc:
        logger.error(f"Error downloading file: {exc}")
        await update.message.reply_text("❌ ERROR: 파일 다운로드 실패.")
        active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "document",
        {
            "chat_id": chat_id,
            "file_data": {
                "file_path": file_path,
                "file_name": filename,
                "file_size": file_size,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent document task to document bot for chat {chat_id}")

    estimated_time = estimate_processing_time("document", {"file_name": filename, "file_size": file_size})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), "document", estimated_time, cancel_event)
    )

    try:
        result_payload = await wait_for_result(chat_id, timeout=1800)
    finally:
        cancel_event.set()
        await progress_task

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏱️ 처리 시간이 초과되었습니다. 다시 시도해주세요.",
        )

    if file_path:
        try:
            os.remove(file_path)
        except Exception:
            pass

    active_tasks.pop(chat_id, None)
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    voice = update.message.voice
    if not voice:
        return

    chat_id = str(update.effective_chat.id)
    duration = voice.duration or 0

    logger.info(f"Voice message: {duration}s")

    if not voice.mime_type or not voice.mime_type.startswith('audio/'):
        await update.message.reply_text("⚠️ WARN: 음성 파일 형식이 올바르지 않습니다.")
        return

    await update.message.reply_text(
        f"🎤 음성을 받았습니다!\n길이: {duration}초"
    )

    active_tasks[chat_id] = {
        "type": "audio",
        "status": "processing",
        "duration": duration,
        "file_id": voice.file_id,
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(voice.file_id)

        ext_map = {
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
        }
        file_ext = ext_map.get(voice.mime_type, '.ogg')

        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"voice_{chat_id}_{int(time.time())}{file_ext}")
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded voice to: {file_path}")

    except Exception as exc:
        logger.error(f"Error downloading voice: {exc}")
        await update.message.reply_text("❌ ERROR: 음성 다운로드 실패.")
        active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "audio",
        {
            "chat_id": chat_id,
            "voice_data": {
                "file_path": file_path,
                "duration": duration,
                "mime_type": voice.mime_type,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent voice task to audio bot for chat {chat_id}")

    estimated_time = estimate_processing_time("audio", {"duration": duration})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), "audio", estimated_time, cancel_event)
    )

    try:
        result_payload = await wait_for_result(chat_id, timeout=1800)
    finally:
        cancel_event.set()
        await progress_task

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏰ 음성 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요.",
        )
        try:
            os.remove(file_path)
        except Exception:
            pass

    active_tasks.pop(chat_id, None)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads"""
    photo = update.message.photo[-1]
    if not photo:
        return

    chat_id = str(update.effective_chat.id)
    file_id = photo.file_id

    logger.info(f"Photo upload: {file_id}")

    await update.message.reply_text("🖼️ 이미지를 받았습니다!")

    active_tasks[chat_id] = {
        "type": "image",
        "status": "processing",
        "file_id": file_id,
        "start_time": datetime.now().strftime("%H:%M:%S"),
    }

    file_path = None

    try:
        file = await context.bot.get_file(file_id)
        import tempfile
        import time
        temp_dir = tempfile.gettempdir()
        file_name = f"image_{chat_id}_{int(time.time())}.jpg"
        file_path = os.path.join(temp_dir, file_name)
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded image to: {file_path}")
    except Exception as exc:
        logger.error(f"Error downloading image: {exc}")
        await update.message.reply_text("❌ ERROR: 이미지 다운로드 실패.")
        active_tasks.pop(chat_id, None)
        return

    messenger.publish_task(
        "image",
        {
            "chat_id": chat_id,
            "image_data": {
                "file_path": file_path,
            },
            "user_id": str(update.effective_user.id),
        },
    )
    logger.info(f"Sent image task to image bot for chat {chat_id}")

    estimated_time = estimate_processing_time("image", {})
    cancel_event = asyncio.Event()
    progress_task = asyncio.create_task(
        send_progress_updates(context.bot, int(chat_id), "image", estimated_time, cancel_event)
    )

    try:
        result_payload = await wait_for_result(chat_id, timeout=1800)
    finally:
        cancel_event.set()
        await progress_task

    if result_payload:
        await _process_result_payload(context.bot, result_payload)
    else:
        await context.bot.send_message(
            chat_id=int(chat_id),
            text="⏰ 이미지 처리가 예상보다 오래 걸려 중단되었어요. 다시 시도해주세요.",
        )
        if file_path:
            try:
                os.remove(file_path)
            except Exception:
                pass

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


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses for automation preferences."""
    query = update.callback_query
    if not query:
        return

    data = query.data or ""
    chat_id = str(query.message.chat.id if query.message else query.from_user.id)

    try:
        await query.answer()
    except Exception as exc:
        logger.warning("Failed to answer callback query: %s", exc)

    if data.startswith("doc_action|"):
        parts = data.split("|")
        if len(parts) != 3:
            return
        _, mode, action = parts

        result_payload = document_followups.get(chat_id)
        if not result_payload:
            await query.edit_message_text("⚠️ 처리할 문서 결과를 찾지 못했어요. 다시 시도해주세요.")
            return

        if mode == "once":
            if action != "none":
                await execute_document_action(action, context.bot, chat_id, result_payload)
            else:
                try:
                    await context.bot.send_message(
                        chat_id=int(chat_id),
                        text="추가 작업 없이 마무리했어요.",
                    )
                except Exception as exc:
                    logger.error("Failed to send no-action confirmation: %s", exc)
            document_followups.pop(chat_id, None)
            await query.edit_message_text("✅ 선택한 작업을 완료했습니다.")
            return

        if mode == "auto":
            preference_store.set_preferences(chat_id, {"mode": "auto", "default_action": action})
            action_label = ACTION_LABELS.get(action, action)
            await query.edit_message_text(
                f"🔁 앞으로 \"{action_label}\" 작업을 자동으로 실행할게요.",
            )
            if action != "none":
                await execute_document_action(action, context.bot, chat_id, result_payload)
            document_followups.pop(chat_id, None)
            return

        if mode == "ask":
            preference_store.set_preferences(chat_id, {"mode": "ask", "default_action": "none"})
            await query.edit_message_text("대화형 모드로 전환했어요. 원하는 작업을 다시 선택해주세요.")
            await prompt_document_followup(context.bot, chat_id)
            return

        if mode == "skip":
            preference_store.set_preferences(chat_id, {"mode": "skip", "default_action": "none"})
            document_followups.pop(chat_id, None)
            await query.edit_message_text("앞으로 요약만 전달하고 후속 작업은 건너뛰겠습니다.")
            return

    elif data.startswith("pref_mode|"):
        _, mode = data.split("|", 1)
        if mode == "auto":
            prefs = preference_store.set_preferences(chat_id, {"mode": "auto"})
        elif mode == "skip":
            prefs = preference_store.set_preferences(chat_id, {"mode": "skip", "default_action": "none"})
        else:
            prefs = preference_store.set_preferences(chat_id, {"mode": "ask", "default_action": "none"})

        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )
        await apply_preferences_to_pending_document(context.bot, chat_id, prefs)

    elif data.startswith("pref_action|"):
        _, action = data.split("|", 1)
        if action == "none":
            prefs = preference_store.set_preferences(chat_id, {"default_action": "none", "mode": "ask"})
        else:
            prefs = preference_store.set_preferences(chat_id, {"default_action": action, "mode": "auto"})
        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )
        await apply_preferences_to_pending_document(context.bot, chat_id, prefs)

    elif data.startswith("pref_open|"):
        prefs = preference_store.get_preferences(chat_id)
        await query.edit_message_text(
            build_settings_message(prefs),
            reply_markup=build_settings_keyboard(prefs),
        )


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
            timeout=2.0,
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
                timeout=2.0,
            )

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Result listener error: %s", exc)


async def wait_for_result(chat_id: str, timeout: int = 1800) -> Optional[Dict[str, Any]]:
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
    """Send document analysis result and trigger follow-up flow."""
    summary = result.get("summary", "N/A")
    extracted = result.get("text", "N/A")
    file_name = result.get("file_name", "문서")

    try:
        await bot.send_message(
            chat_id=int(chat_id),
            text=(
                f"📄 문서 분석 완료!\n"
                f"파일명: {file_name}\n\n"
                f"요약:\n{summary}\n\n"
                f"원문 발췌:\n{extracted}"
            ),
        )
    except Exception as exc:
        logger.error("Error sending document result: %s", exc)

    document_followups[chat_id] = result
    prefs = preference_store.get_preferences(chat_id)
    await apply_preferences_to_pending_document(bot, chat_id, prefs)


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
    application.add_handler(CommandHandler("settings", handle_settings))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

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
